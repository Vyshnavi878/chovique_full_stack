"""Main router aggregator."""

from fastapi import APIRouter

from app.api.v1 import auth
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_PREFIX)
api_router.include_router(auth.router)

