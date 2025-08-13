from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import logging
from src import __version__
from .routes import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GitHub Repository Selector API",
    description="""
    API for discovering Python repositories suitable for SWE Challenge V3 contributions.
    
    ## Features
    
    * **Search Repositories**: Find Python repositories with smart filtering
    * **Analyze Suitability**: Comprehensive analysis of repository contribution potential
    * **User-Specific Tracking**: Personal database of discovered repositories
    * **Export Capabilities**: Export findings in multiple formats (JSON, CSV, YAML, Markdown)
    * **Fresh Results**: Avoid seeing the same repositories repeatedly
    
    ## Authentication
    
    Pass your user ID in the `X-User-ID` header to maintain personal repository history.
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "repository-selector",
            "description": "Core repository discovery and analysis endpoints",
        }
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response

# Include API routes
app.include_router(router)

@app.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "message": "GitHub Repository Selector API",
        "version": __version__,
        "description": "API for discovering Python repositories suitable for SWE Challenge V3",
        "endpoints": {
            "documentation": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
            "search": "/api/v1/search",
            "analyze": "/api/v1/analyze/{owner}/{repo}",
            "stats": "/api/v1/users/{user_id}/stats",
            "export": "/api/v1/export"
        },
        "features": [
            "User-specific repository tracking",
            "Comprehensive repository analysis",
            "Fresh results filtering",
            "Multiple export formats",
            "GitHub rate limit awareness"
        ]
    }

@app.get("/info")
async def api_info():
    """Detailed API information and usage guidelines"""
    return {
        "api_name": "GitHub Repository Selector",
        "version": __version__,
        "purpose": "Discover Python repositories suitable for SWE Challenge V3 contributions",
        "usage": {
            "authentication": "Optional: Pass X-User-ID header for personalized tracking",
            "rate_limits": "Respects GitHub API rate limits (5000 requests/hour)",
            "user_tracking": "Each user gets personalized repository history"
        },
        "analysis_criteria": {
            "activity_score": "Repository maintenance and recent activity (30%)",
            "opportunity_score": "Available contribution opportunities (35%)",
            "complexity_score": "Project manageability and size (20%)",
            "maintainability_score": "Documentation and guidelines (15%)"
        },
        "supported_formats": ["json", "csv", "yaml", "markdown"],
        "example_usage": {
            "search": "POST /api/v1/search with min_stars, max_stars, limit",
            "analyze": "GET /api/v1/analyze/owner/repository",
            "stats": "GET /api/v1/users/your_username/stats"
        }
    }

# Custom exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed messages"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request validation failed",
            "details": exc.errors(),
            "body": str(exc.body) if hasattr(exc, 'body') else None
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with consistent format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "status_code": exc.status_code,
            "message": exc.detail,
            "endpoint": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if app.debug else "Contact API administrator"
        }
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Execute on API startup"""
    logger.info(f"GitHub Repository Selector API v{__version__} starting up...")
    logger.info("API documentation available at /docs")

@app.on_event("shutdown")
async def shutdown_event():
    """Execute on API shutdown"""
    logger.info("GitHub Repository Selector API shutting down...")

# Health check for load balancers/monitoring
@app.get("/ping")
async def ping():
    """Simple ping endpoint for load balancers"""
    return {"status": "ok", "timestamp": time.time()}
