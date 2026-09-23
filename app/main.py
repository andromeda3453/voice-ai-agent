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


# Health check endpoint
@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint for platform monitoring."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/", tags=["System"])
def root():
    """Service root with overview."""
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "patients": "/patients",
            "vapi_webhook": "/vapi/webhook",
        },
    }


# Include Routers
app.include_router(patients.router)
app.include_router(vapi_tools.router)
