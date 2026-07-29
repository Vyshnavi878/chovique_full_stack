import cloudinary
from app.core.config import settings


def configure_cloudinary():
    """Configure Cloudinary SDK using application settings."""
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


# Configure on module import
configure_cloudinary()
