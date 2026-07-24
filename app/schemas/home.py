from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductResponse


# ==========================================================
# Banner Response
# ==========================================================

class BannerResponse(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    tag: Optional[str] = None
    image: str
    buttonText: Optional[str] = None
    link: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, banner) -> "BannerResponse":
        return cls(
            id=banner.id,
            title=banner.title,
            subtitle=banner.subtitle,
            tag=banner.tag,
            image=banner.image,
            buttonText=banner.button_text,
            link=banner.link,
        )


# ==========================================================
# Testimonial Response
# ==========================================================

class TestimonialResponse(BaseModel):
    id: str
    author: str
    title: Optional[str] = None
    text: str
    stars: float = 5.0
    initials: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_model(cls, testimonial) -> "TestimonialResponse":
        return cls(
            id=testimonial.id,
            author=testimonial.author,
            title=testimonial.title,
            text=testimonial.text,
            stars=testimonial.rating,
            initials=testimonial.initials,
        )


# ==========================================================
# Stats Response
# ==========================================================

class StatsResponse(BaseModel):
    happy_customers: int = 50000
    unique_flavors: int = 120
    countries_shipped: int = 15
    five_star_reviews_percent: int = 98


# ==========================================================
# Contact Info Response
# ==========================================================

class ContactInfoResponse(BaseModel):
    email: str = ""
    phone: str = ""
    address: str = ""
    instagram: str = ""
    facebook: str = ""
    twitter: str = ""


from app.schemas.category import CategoryResponse
from app.schemas.faq import FAQResponse


# ==========================================================
# Home Page Response
# ==========================================================

class HomePageResponse(BaseModel):
    banners: list[BannerResponse] = []
    categories: list[CategoryResponse] = []
    featured_products: list[ProductResponse] = []
    bestsellers: list[ProductResponse] = []
    new_arrivals: list[ProductResponse] = []
    testimonials: list[TestimonialResponse] = []
    faqs: list[FAQResponse] = []
    stats: StatsResponse = StatsResponse()
    contact: ContactInfoResponse = ContactInfoResponse()
