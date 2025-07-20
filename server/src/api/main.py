"""Main FastAPI application."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from src.api.auth import router as auth_router
from src.api.llm import router as llm_router
from src.config.settings import settings
from src.utils.logging import setup_app_logging
from src.api.exception_handlers import (
    register_exception_handlers,
)

# Create logger
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="MCP Server",
    description="MCP Server for AI evaluations and plugin integration",
    version="0.1.0",
    docs_url="/docs" if settings.show_docs else None,
    redoc_url="/redoc" if settings.show_docs else None,
)

# Set up logging
setup_app_logging(app, {"log_level": settings.log_level})

# Register exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router
api_router = APIRouter(prefix="/api/v1")

# Register routers
api_router.include_router(auth_router)
api_router.include_router(llm_router)

# Include API router
app.include_router(api_router)

# Health check endpoint
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Run startup tasks."""
    logger.info("Starting MCP Server")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.cors_origins}")
    logger.info(f"API docs: {settings.show_docs}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run shutdown tasks."""
    logger.info("Shutting down MCP Server") 