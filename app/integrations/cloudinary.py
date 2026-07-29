"""
Cloudinary Integration backward compatibility wrapper.
Proxies calls to app.services.cloudinary_service.
"""
from app.services.cloudinary_service import cloudinary_service, CloudinaryService

__all__ = ["cloudinary_service", "CloudinaryService"]
