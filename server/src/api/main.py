"""
Main FastAPI application entry point.

This module initializes the FastAPI application, includes all routers,
sets up middleware, and starts the server.
"""

import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.llm.proxy.router import router as llm_router
from src.api.exception_handlers import register_exception_handlers
from src.config.settings import settings

# Configure logging using our centralized logging module
from src.utils.logging import configure_logging, get_logger

# Ensure log directory exists
os.makedirs(settings.log_dir, exist_ok=True)

configure_logging(settings.log_level)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MCP Server API",
    description="Multi-Client Platform Server API",
    version="1.0.0",
    docs_url="/docs" if settings.debug_mode else None,
    redoc_url="/redoc" if settings.debug_mode else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(llm_router, prefix="/api/v1")

# Register exception handlers
register_exception_handlers(app)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {"message": "MCP Server API"}


@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting MCP Server API on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug_mode
    )