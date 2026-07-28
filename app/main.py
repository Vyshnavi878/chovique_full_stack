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

app.add_middleware(AuditLogMiddleware)

raw_origins = settings.ALLOWED_ORIGINS
origins_list = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
if raw_origins:
    if isinstance(raw_origins, list):
        origins_list.extend([o for o in raw_origins if o not in origins_list])
    elif isinstance(raw_origins, str):
        for o in raw_origins.split(","):
            o_clean = o.strip()
            if o_clean and o_clean not in origins_list:
                origins_list.append(o_clean)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_list,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
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
