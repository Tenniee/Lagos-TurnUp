# config/cloudinary_config.py
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import os
from typing import Optional
import io

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

class CloudinaryService:
    """Service class for Cloudinary operations"""
    
    @staticmethod
    def upload_banner_image(file_content: bytes, filename: str) -> dict:
        """Upload banner image to Cloudinary"""
        try:
            upload_options = {
                "folder": "banners",
                "public_id": f"banner_{filename.split('.')[0]}_{cloudinary.utils.now()}",
                "resource_type": "image",
                "transformation": [
                    {"width": 1200, "height": 400, "crop": "limit"},
                    {"quality": "auto"},
                    {"fetch_format": "auto"}
                ],
                "allowed_formats": ["jpg", "jpeg", "png", "webp"]
            }
            
            result = cloudinary.uploader.upload(
                io.BytesIO(file_content),
                **upload_options
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"]
            }
            
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {str(e)}")




    
    @staticmethod
    def upload_profile_image(file_content: bytes, filename: str) -> dict:
        """Upload profile image to Cloudinary"""
        try:
            upload_options = {
                "folder": "profiles",
                "public_id": f"profile_{filename.split('.')[0]}_{cloudinary.utils.now()}",
                "resource_type": "image",
                "transformation": [
                    {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},  # Square crop focusing on face
                    {"quality": "auto"},
                    {"fetch_format": "auto"}
                ],
                "allowed_formats": ["jpg", "jpeg", "png", "webp"]
            }
            
            result = cloudinary.uploader.upload(
                io.BytesIO(file_content),
                **upload_options
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"]
            }
            
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {str(e)}")


            
    
    @staticmethod
    def upload_event_image(file_content: bytes, filename: str) -> dict:
        """Upload event image to Cloudinary"""
        try:
            upload_options = {
                "folder": "events",
                "public_id": f"event_{filename.split('.')[0]}_{cloudinary.utils.now()}",
                "resource_type": "image",
                "transformation": [
                    {"width": 800, "height": 600, "crop": "limit"},
                    {"quality": "auto"},
                    {"fetch_format": "auto"}
                ],
                "allowed_formats": ["jpg", "jpeg", "png", "webp"]
            }
            
            result = cloudinary.uploader.upload(
                io.BytesIO(file_content),
                **upload_options
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"]
            }
            
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {str(e)}")
    
    @staticmethod
    def upload_spot_image(file_content: bytes, filename: str, spot_name: str = "") -> dict:
        """Upload spot image to Cloudinary"""
        try:
            upload_options = {
                "folder": "spots",
                "public_id": f"spot_{spot_name}_{filename.split('.')[0]}_{cloudinary.utils.now()}",
                "resource_type": "image",
                "transformation": [
                    {"width": 1000, "height": 800, "crop": "limit"},
                    {"quality": "auto"},
                    {"fetch_format": "auto"}
                ],
                "allowed_formats": ["jpg", "jpeg", "png", "webp"]
            }
            
            result = cloudinary.uploader.upload(
                io.BytesIO(file_content),
                **upload_options
            )
            
            return {
                "url": result["secure_url"],
                "public_id": result["public_id"]
            }
            
        except Exception as e:
            raise Exception(f"Cloudinary upload failed: {str(e)}")
    
    @staticmethod
    def delete_image(public_id: str) -> bool:
        """Delete image from Cloudinary"""
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            print(f"Error deleting image from Cloudinary: {str(e)}")
            return False