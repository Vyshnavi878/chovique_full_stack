import io
import logging
from typing import Optional
import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.cloudinary import configure_cloudinary

logger = logging.getLogger(__name__)

# Constants & Limits
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm"}


class CloudinaryService:
    """Service layer for handling Cloudinary image and video operations."""

    def __init__(self):
        configure_cloudinary()

    def validate_file_extension(self, filename: str, allowed_extensions: set) -> str:
        """Validate filename extension against allowed set."""
        if not filename or "." not in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. File must have an extension.",
            )
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in allowed_extensions:
            allowed_str = ", ".join(sorted(allowed_extensions))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type '.{ext}'. Allowed types: {allowed_str}.",
            )
        return ext

    def validate_file_size(self, file_bytes: bytes, max_size: int, file_type: str):
        """Validate byte length against size limit."""
        if len(file_bytes) > max_size:
            max_mb = max_size // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{file_type.capitalize()} file size exceeds maximum limit of {max_mb}MB.",
            )

    async def upload_image(
        self,
        file: UploadFile,
        folder: str = "chocolate-world/products",
    ) -> str:
        """
        Validate and upload an image file to Cloudinary.
        Returns secure_url.
        """
        self.validate_file_extension(file.filename or "", ALLOWED_IMAGE_EXTENSIONS)
        file_bytes = await file.read()
        self.validate_file_size(file_bytes, MAX_IMAGE_SIZE, "image")

        try:
            res = cloudinary.uploader.upload(
                io.BytesIO(file_bytes),
                folder=folder,
                overwrite=True,
                resource_type="image",
            )
            secure_url = res.get("secure_url") or res.get("url")
            if not secure_url:
                raise ValueError("Cloudinary response missing URL.")
            logger.info("Uploaded image to Cloudinary folder '%s': %s", folder, secure_url)
            return secure_url
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Cloudinary image upload failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image to Cloudinary: {str(e)}",
            )

    async def upload_video(
        self,
        file: UploadFile,
        folder: str = "chocolate-world/reels",
    ) -> str:
        """
        Validate and upload a video file to Cloudinary with resource_type='video'.
        Returns secure_url.
        """
        self.validate_file_extension(file.filename or "", ALLOWED_VIDEO_EXTENSIONS)
        file_bytes = await file.read()
        self.validate_file_size(file_bytes, MAX_VIDEO_SIZE, "video")

        try:
            res = cloudinary.uploader.upload(
                io.BytesIO(file_bytes),
                folder=folder,
                overwrite=True,
                resource_type="video",
            )
            secure_url = res.get("secure_url") or res.get("url")
            if not secure_url:
                raise ValueError("Cloudinary response missing URL.")
            logger.info("Uploaded video to Cloudinary folder '%s': %s", folder, secure_url)
            return secure_url
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Cloudinary video upload failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload video to Cloudinary: {str(e)}",
            )

    def delete_media(self, public_id: str, resource_type: str = "image") -> bool:
        """Delete media asset from Cloudinary by public ID."""
        try:
            res = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            return res.get("result") == "ok"
        except Exception as e:
            logger.error("Failed to delete Cloudinary asset '%s': %s", public_id, e)
            return False

    def extract_public_id(self, url: str) -> Optional[str]:
        """Extract public ID from a Cloudinary URL to be used for deletion."""
        if not url or "cloudinary" not in url:
            return None
        try:
            parts = url.split("/upload/")
            if len(parts) < 2:
                return None
            path_after_upload = parts[1]
            
            path_parts = path_after_upload.split("/")
            if len(path_parts) > 1 and path_parts[0].startswith("v") and path_parts[0][1:].isdigit():
                path_parts = path_parts[1:]
            
            public_id_with_ext = "/".join(path_parts)
            public_id = public_id_with_ext.rsplit(".", 1)[0]
            return public_id
        except Exception:
            return None

cloudinary_service = CloudinaryService()
