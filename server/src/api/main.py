"""Main FastAPI application."""

from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Dict, Any, List, Tuple, AsyncGenerator
import structlog
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
import os

from src.config.settings import settings
from src.api.auth import (
    authenticate_user, create_access_token, get_current_active_user,
    Token, User, UserCreate, create_user, require_admin, require_read
)
from src.core.plugin_system.plugin_manager import PluginManager
from src.core.routing.semantic_router import SemanticRouter
from src.core.routing.agentic_framework import AgenticFramework
from src.core.llm import LLMProviderFactory
from src.api.models import (
    QueryRequest, QueryResponse, PluginInfo, HealthResponse,
    PluginExecuteRequest, PluginExecuteResponse
)
from src.api.exception_handlers import register_exception_handlers

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

def get_or_create_metrics() -> Tuple[Counter, Histogram]:
    """Get or create Prometheus metrics for monitoring.
    
    Creates counter and histogram metrics for tracking:
    - Request counts by endpoint and status
    - Request duration by endpoint
    
    Returns:
        Tuple of (request_count, request_duration) metrics
    """
    global request_count, request_duration
    
    if request_count is None:
        request_count = Counter(
            'mcp_server_requests_total',
            'Total requests by endpoint and status',
            ['endpoint', 'status']
        )
    
    if request_duration is None:
        request_duration = Histogram(
            'mcp_server_request_duration_seconds',
            'Request duration by endpoint',
            ['endpoint']
        )
    
    return request_count, request_duration

# Global instances
plugin_manager: PluginManager = None
semantic_router: SemanticRouter = None
agentic_framework: AgenticFramework = None
request_count: Counter = None
request_duration: Histogram = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle events.
    
    Handles startup and shutdown tasks:
    - Initializes plugin manager and loads plugins
    - Sets up semantic router and agentic framework
    - Cleans up resources on shutdown
    
    Args:
        app: FastAPI application instance
        
    Yields:
        Control back to FastAPI during application runtime
    """
    global plugin_manager, semantic_router, agentic_framework
    
    logger.info("Starting MCP Server")
    
    try:
        plugin_manager = PluginManager(
            plugin_directory=settings.plugin_directory,
            auto_reload=settings.plugin_auto_reload
        )
        await plugin_manager.initialize()
        
        # LinkedIn requires authentication cookie, skip if not provided
        if settings.linkedin_cookie or os.getenv("LINKEDIN_COOKIE"):
            await plugin_manager.load_plugin("linkedin_external")
        else:
            logger.warning("LinkedIn plugin not loaded - no LINKEDIN_COOKIE environment variable set")
        
        # Initialize shared LLM provider for consistent responses across components
        llm_provider = LLMProviderFactory.create_provider(
            provider_name=settings.llm_provider,
            api_key=settings.get_llm_api_key(),
            model=settings.get_llm_model()
        )
        
        semantic_router = SemanticRouter(
            plugin_manager=plugin_manager,
            llm_provider=llm_provider,
            temperature=settings.llm_temperature
        )
        
        agentic_framework = AgenticFramework(
            semantic_router=semantic_router,
            llm_provider=llm_provider,
            max_retries=settings.agentic_max_retries
        )
        
        logger.info("MCP Server started successfully")
        yield
        
    finally:
        logger.info("Shutting down MCP Server")
        if plugin_manager:
            await plugin_manager.shutdown()
        logger.info("MCP Server shutdown complete")

app = FastAPI(
    title="MCP Server",
    description="Extensible Multi-Client Platform Server with semantic routing",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

register_exception_handlers(app)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Health check endpoint for monitoring.
    
    Returns basic health status and system information.
    Used by load balancers and monitoring systems.
    
    Returns:
        HealthResponse with status and plugin count
    """
    return HealthResponse(
        status="healthy",
        environment=settings.environment,
        plugins_loaded=len(plugin_manager.get_loaded_plugins()) if plugin_manager else 0
    )


# Metrics endpoint
@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    """Prometheus metrics endpoint.
    
    Exposes application metrics in Prometheus format for monitoring.
    Only available when metrics are enabled.
    
    Returns:
        Plain text response with Prometheus metrics
        
    Raises:
        HTTPException: If metrics are not enabled
    """
    if not settings.prometheus_enabled:
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type="text/plain")


# Authentication endpoints
@app.post(f"{settings.api_prefix}/auth/token", response_model=Token, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and generate access token.
    
    OAuth2 compatible token endpoint for user authentication.
    
    Args:
        form_data: OAuth2 form with username and password
        
    Returns:
        Token response with access token and type
        
    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": user.scopes},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@app.post(f"{settings.api_prefix}/auth/register", response_model=User, tags=["auth"])
async def register(
    user_create: UserCreate,
    current_user: User = Depends(require_admin)
):
    """Register a new user (admin only).
    
    Creates a new user account with the specified credentials.
    Only administrators can create new users.
    
    Args:
        user_create: User creation data
        current_user: Current authenticated admin user
        
    Returns:
        Created user information
    """
    return create_user(user_create)


@app.get(f"{settings.api_prefix}/auth/me", response_model=User, tags=["auth"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information.
    
    Returns information about the authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information
    """
    return current_user


# Plugin endpoints
@app.get(f"{settings.api_prefix}/plugins", response_model=List[PluginInfo], tags=["plugins"])
async def list_plugins(current_user: User = Depends(require_read)):
    """List all available plugins.
    
    Returns information about all loaded plugins including
    their capabilities and configuration.
    
    Args:
        current_user: Authenticated user with read permissions
        
    Returns:
        List of plugin information
    """
    plugins = []
    for name in plugin_manager.get_loaded_plugins():
        metadata = plugin_manager.get_plugin_metadata(name)
        if metadata:
            plugins.append(PluginInfo(
                name=metadata.name,
                version=metadata.version,
                description=metadata.description,
                capabilities=metadata.capabilities,
                loaded=True
            ))
    return plugins


@app.get(f"{settings.api_prefix}/plugins/{{plugin_name}}", response_model=Dict[str, Any], tags=["plugins"])
async def get_plugin_details(
    plugin_name: str,
    current_user: User = Depends(require_read)
):
    """Get detailed information about a specific plugin.
    
    Args:
        plugin_name: Name of the plugin
        current_user: Authenticated user with read permissions
        
    Returns:
        Detailed plugin metadata
        
    Raises:
        HTTPException: If plugin not found
    """
    metadata = plugin_manager.get_plugin_metadata(plugin_name)
    if not metadata:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {
        "name": plugin_name,
        "metadata": metadata.dict()
    }


@app.post(f"{settings.api_prefix}/plugins/{{plugin_name}}/execute", response_model=PluginExecuteResponse, tags=["plugins"])
async def execute_plugin(
    plugin_name: str,
    request: PluginExecuteRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Execute a specific plugin directly.
    
    Bypasses semantic routing and executes the named plugin.
    
    Args:
        plugin_name: Name of the plugin to execute
        request: Plugin execution request with action and parameters
        current_user: Authenticated user
        
    Returns:
        Plugin execution response
        
    Raises:
        HTTPException: If plugin not found or execution fails
    """
    req_count, req_duration = get_or_create_metrics()
    endpoint = f"/plugins/{plugin_name}/execute"

    try:
        response = await plugin_manager.execute_plugin(plugin_name, request.to_plugin_request())
        req_count.labels(endpoint=endpoint, status="success").inc()
        
        return PluginExecuteResponse(
            request_id=response.request_id,
            status=response.status,
            data=response.data,
            error=response.error,
            metadata=response.metadata
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Plugin not found")
    except Exception as e:
        logger.error("Plugin execution failed", plugin=plugin_name, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Query processing endpoints
@app.post(f"{settings.api_prefix}/query", response_model=QueryResponse, tags=["query"])
async def process_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Process a natural language query with intelligent routing.
    
    Uses semantic routing to understand the query intent and
    route to appropriate plugins. Supports both simple and
    complex multi-step queries.
    
    Args:
        request: Query request with natural language text
        current_user: Authenticated user
        
    Returns:
        Query response with results and execution details
        
    Raises:
        HTTPException: If query processing fails
    """
    req_count, req_duration = get_or_create_metrics()
    endpoint = "/query"
    
    try:
        # Use semantic routing for complex queries, direct execution for simple ones
        if request.use_reflection:
            # Agentic framework provides self-correction and goal-oriented processing
            result = await agentic_framework.process_with_reflection(
                request.query,
                max_attempts=request.max_attempts
            )
            
            # Generate explanation
            explanation = await agentic_framework.explain_reasoning(result)
            
            return QueryResponse(
                query=request.query,
                status="success",
                result=result,
                explanation=explanation
            )
        else:
            # Use semantic router directly
            result = await semantic_router.process_query(request.query)
            
            return QueryResponse(
                query=request.query,
                status="success",
                result=result,
                explanation=result.get("reasoning", "")
            )
    
    except Exception as e:
        import traceback
        logger.error("Query processing failed", 
                    query=request.query, 
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc())
        return QueryResponse(
            query=request.query,
            status="error",
            result=None,
            error=str(e),
            explanation=None
        )


@app.post(f"{settings.api_prefix}/query/analyze", response_model=Dict[str, Any], tags=["query"])
async def analyze_query(
    request: QueryRequest,
    current_user: User = Depends(require_read)
):
    """Analyze a query without executing it.
    
    Useful for understanding how the system would process a query
    without actually running it. Shows routing decisions and
    complexity analysis.
    
    Args:
        request: Query request to analyze
        current_user: Authenticated user with read permissions
        
    Returns:
        Analysis results including routing and complexity
        
    Raises:
        HTTPException: If analysis fails
    """
    try:
        # Extract goal
        goal = await agentic_framework.extract_goal(request.query)
        
        # Analyze complexity
        is_complex, reasoning = await semantic_router.analyze_complexity(request.query)
        
        # Get routing or planning
        if is_complex:
            plan = await semantic_router.plan_multi_step(request.query)
            routing_info = {"type": "multi_step", "plan": plan.model_dump()}
        else:
            routing = await semantic_router.route(request.query)
            routing_info = {"type": "single_step", "routing": routing.model_dump()}
        
        return {
            "query": request.query,
            "goal": goal.model_dump(),
            "is_complex": is_complex,
            "complexity_reasoning": reasoning,
            "routing_info": routing_info
        }
    
    except Exception as e:
        logger.error("Query analysis failed", query=request.query, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Admin endpoints
@app.post(f"{settings.api_prefix}/admin/plugins/reload", tags=["admin"])
async def reload_plugins(current_user: User = Depends(require_admin)):
    """Reload all plugins (admin only).
    
    Reloads the plugin system, useful for development or
    when plugins have been updated.
    
    Args:
        current_user: Authenticated admin user
        
    Returns:
        Success message with plugin count
    """
    await plugin_manager.reload_plugins()
    return {"message": "Plugins reloaded", "count": len(plugin_manager.get_loaded_plugins())}

@app.delete(f"{settings.api_prefix}/admin/plugins/{{plugin_name}}", tags=["admin"])
async def unload_plugin(
    plugin_name: str,
    current_user: User = Depends(require_admin)
):
    """Unload a specific plugin (admin only).
    
    Removes a plugin from the system without affecting others.
    
    Args:
        plugin_name: Name of plugin to unload
        current_user: Authenticated admin user
        
    Returns:
        Success message
    """
    await plugin_manager.unload_plugin(plugin_name)
    return {"message": f"Plugin '{plugin_name}' unloaded"}


# Root endpoint
@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with API information.
    
    Returns:
        Basic API information and documentation links
    """
    return {
        "name": "MCP Server",
        "version": "0.1.0",
        "description": "Extensible Multi-Client Platform Server",
        "docs": "/docs" if settings.is_development else None,
        "api_prefix": settings.api_prefix
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    ) 