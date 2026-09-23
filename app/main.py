"""FastAPI Main Application Entrypoint."""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import init_db
from app.routers import patients, vapi_tools

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("patient_registration")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown tasks."""
    logger.info("Starting up Voice AI Patient Registration service...")
    init_db()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down service...")


app = FastAPI(
    title=settings.app_name,
    description="A voice-based AI agent backend for conversational patient registration and REST API querying.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom validation error handler for consistent envelope responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = [f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in errors]
    joined_msg = "; ".join(error_messages)
    logger.warning(f"Validation error on {request.url.path}: {joined_msg}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"data": None, "error": f"Validation error: {joined_msg}"},
    )


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# Health check endpoint
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for platform monitoring."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/api", tags=["System"])
def api_root():
    """Service API overview."""
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "dashboard": "/dashboard",
        "endpoints": {
            "patients": "/patients",
            "vapi_webhook": "/vapi/webhook",
        },
    }


# Static files and Web Dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    async def serve_dashboard():
        """Serve Web UI Dashboard."""
        return FileResponse(os.path.join(static_dir, "index.html"))


# Include Routers
app.include_router(patients.router)
app.include_router(vapi_tools.router)

