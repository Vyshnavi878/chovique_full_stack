import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    MaxAttemptsExceededError,
    OTPError,
)
from app.db.session import AsyncSessionLocal, init_db

# ==========================================================
# Logging Configuration
# ==========================================================

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if not getattr(settings, "DB_ECHO", False):
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ==========================================================
# Lifespan
# ==========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Create tables
    await init_db()
    logger.info("Database tables initialized.")

    logger.info("Application startup complete.")
    yield
    logger.info("Application shutting down.")


# ==========================================================
# App
# ==========================================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

import os
from fastapi.staticfiles import StaticFiles
from app.middleware.audit import AuditLogMiddleware

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# NOTE: Middleware runs in REVERSE order of registration.
# CORS must be added LAST so it executes FIRST (outermost layer),
# ensuring preflight OPTIONS and all error responses include CORS headers.
app.add_middleware(AuditLogMiddleware)

if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )



app.include_router(api_router)


# ==========================================================
# Global Exception Handlers
# ==========================================================

@app.exception_handler(MaxAttemptsExceededError)
async def max_attempts_handler(request: Request, exc: MaxAttemptsExceededError):
    return JSONResponse(
        status_code=429,
        content={"detail": exc.message},
    )


@app.exception_handler(OTPError)
async def otp_error_handler(request: Request, exc: OTPError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message},
    )


@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
    )


@app.exception_handler(AuthorizationError)
async def authz_error_handler(request: Request, exc: AuthorizationError):
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message},
    )


# ==========================================================
# Health Check
# ==========================================================

@app.get("/health")
def health_check():
    return {"status": "ok"}
