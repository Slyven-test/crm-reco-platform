"""FastAPI application entry point."""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from datetime import datetime

from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Wine Recommendation API",
    description="REST API for personalized wine recommendations",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)


# ============================================================================
# Root Endpoints
# ============================================================================

@app.get("/", tags=["health"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "Wine Recommendation API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "openapi": "/api/openapi.json",
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "details": str(exc),
        },
    )


# ============================================================================
# Custom OpenAPI Schema
# ============================================================================

def custom_openapi():
    """Customize OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Wine Recommendation API",
        version="1.0.0",
        description="REST API for personalized wine recommendations with multiple scenarios",
        routes=app.routes,
    )
    
    # Add API key security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "api_key": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on startup."""
    logger.info("Wine Recommendation API starting...")
    logger.info(f"Docs available at: /api/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on shutdown."""
    logger.info("Wine Recommendation API shutting down...")


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
