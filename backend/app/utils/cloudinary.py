import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True
)

def upload_image(file: UploadFile, folder: str = "users") -> str:
    """
    Uploads an image to Cloudinary and returns the secure URL.
    """
    result = cloudinary.uploader.upload(
        file.file,
        folder=folder,
        resource_type="image"
    )
    return result.get("secure_url")
