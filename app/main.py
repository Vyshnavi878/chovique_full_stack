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
from app.services.superadmin_service import ensure_superadmin_exists

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

    # Additional enum & type migrations for PostgreSQL
    try:
        from sqlalchemy import text
        from app.db.session import engine
        async with engine.connect() as conn:
            autocommit_conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            if "postgresql" in engine.dialect.name:
                for val in ["Gift Hamper", "Gift Hampers", "Signature"]:
                    try:
                        await autocommit_conn.execute(text(f"ALTER TYPE product_badge ADD VALUE IF NOT EXISTS '{val}';"))
                    except Exception:
                        pass
                try:
                    await autocommit_conn.execute(text("ALTER TABLE products ALTER COLUMN badge TYPE VARCHAR(50) USING badge::text;"))
                except Exception:
                    pass
            logger.info("Database auto-migrations executed successfully.")
    except Exception as e:
        logger.warning("Database migration note: %s", e)

    # Ensure superadmin, initial banners, testimonials, and products exist
    try:
        async with AsyncSessionLocal() as db:
            await ensure_superadmin_exists(db)
    except Exception as e:
        logger.error("Startup initialization failed: %s", e)




    logger.info("Application startup complete.")
    yield
    logger.info("Application shutting down.")


# ==========================================================
# App
# ==========================================================

from fastapi.responses import HTMLResponse

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url=None,
)

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html = f"""<!DOCTYPE html>
<html>
<head>
<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
<link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
<title>{settings.APP_NAME} - Swagger UI</title>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
<script>
window.onload = function() {{
    window.ui = SwaggerUIBundle({{
        url: '{app.openapi_url}',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
            SwaggerUIBundle.presets.apis,
            SwaggerUIStandalonePreset
        ],
        plugins: [
            SwaggerUIBundle.plugins.DownloadUrl
        ],
        requestInterceptor: function(req) {{
            if (req.method && !['GET', 'HEAD', 'OPTIONS'].includes(req.method.toUpperCase())) {{
                const cookieValue = `; ${{document.cookie}}`;
                const parts = cookieValue.split(`; csrf_token=`);
                if (parts.length === 2) {{
                    const token = parts.pop().split(';').shift();
                    if (token) {{
                        req.headers['X-CSRF-Token'] = token;
                    }}
                }}
            }}
            return req;
        }}
    }});
}};
</script>
</body>
</html>"""
    return HTMLResponse(html)

import os
from app.middleware.csrf_middleware import CSRFMiddleware
from app.middleware.audit import AuditLogMiddleware
from app.middleware.logging_middleware import LoggingMiddleware

# NOTE: Middleware runs in REVERSE order of registration.
# CORS must be added LAST so it executes FIRST (outermost layer),
# ensuring preflight OPTIONS and all error responses include CORS headers.
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(LoggingMiddleware)

if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
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
