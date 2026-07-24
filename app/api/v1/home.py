from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.home_service import HomeService
from app.schemas.home import (
    BannerResponse,
    ContactInfoResponse,
    HomePageResponse,
    StatsResponse,
    TestimonialResponse,
)

router = APIRouter(prefix="/home", tags=["Home Page"])


# ======================================================
# GET HOME PAGE DATA (AGGREGATED)
# ======================================================

@router.get(
    "",
    response_model=HomePageResponse,
    summary="Get aggregated home page data",
)
async def get_home_page(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns all data needed for the landing page in a single call:
    banners, featured products, bestsellers, new arrivals,
    testimonials, stats, and contact info.
    """

    service = HomeService(db)
    return await service.get_home_page_data()


# ======================================================
# GET BANNERS
# ======================================================

@router.get(
    "/banners",
    response_model=list[BannerResponse],
    summary="Get active banners",
)
async def get_banners(
    db: AsyncSession = Depends(get_db),
):
    service = HomeService(db)
    return await service.get_banners()


# ======================================================
# GET TESTIMONIALS
# ======================================================

@router.get(
    "/testimonials",
    response_model=list[TestimonialResponse],
    summary="Get testimonials",
)
async def get_testimonials(
    db: AsyncSession = Depends(get_db),
):
    service = HomeService(db)
    return await service.get_testimonials()


# ======================================================
# GET STATS
# ======================================================

@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get site stats",
)
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    service = HomeService(db)
    return await service.get_stats()


# ======================================================
# GET CONTACT INFO
# ======================================================

@router.get(
    "/contact",
    response_model=ContactInfoResponse,
    summary="Get contact information",
)
async def get_contact(
    db: AsyncSession = Depends(get_db),
):
    service = HomeService(db)
    return await service.get_contact()


@router.get(
    "/reels",
    summary="Get active Instagram reels",
)
async def get_reels(
    db: AsyncSession = Depends(get_db),
):
    service = HomeService(db)
    return await service.get_reels()
