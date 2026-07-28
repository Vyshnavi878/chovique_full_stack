import logging
import os
import uuid
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class CloudinaryIntegration:
    """
    Cloudinary image upload integration wrapper.
    Falls back to local file storage with absolute URL if Cloudinary credentials are not provided.
    """

    @property
    def cloud_name(self) -> str:
        return settings.CLOUDINARY_CLOUD_NAME

    @property
    def api_key(self) -> str:
        return settings.CLOUDINARY_API_KEY

    @property
    def api_secret(self) -> str:
        return settings.CLOUDINARY_API_SECRET

    async def upload_image(
        self,
        file_bytes: bytes,
        filename: str = "upload.jpg",
        folder: str = "products",
    ) -> str:
        """
        Upload an image to Cloudinary or save locally.
        Returns the public image URL.
        """
        if self.cloud_name and self.api_key and self.api_secret:
            try:
                import io
                import cloudinary
                import cloudinary.uploader

                cloudinary.config(
                    cloud_name=self.cloud_name,
                    api_key=self.api_key,
                    api_secret=self.api_secret,
                )
                res = cloudinary.uploader.upload(
                    io.BytesIO(file_bytes),
                    folder=folder,
                    overwrite=True,
                    resource_type="image",
                )
                url = res.get("secure_url") or res.get("url")
                logger.info("Cloudinary upload successful: %s", url)
                return url
            except Exception as e:
                logger.error("Cloudinary upload failed: %s. Falling back to local storage.", e)


        # Fallback local storage
        ext = filename.split(".")[-1] if "." in filename else "jpg"
        save_dir = os.path.join("static", folder)
        os.makedirs(save_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex[:12]}.{ext}"
        filepath = os.path.join(save_dir, unique_name)

        with open(filepath, "wb") as f:
            f.write(file_bytes)

        return f"/static/{folder}/{unique_name}"


cloudinary_service = CloudinaryIntegration()

