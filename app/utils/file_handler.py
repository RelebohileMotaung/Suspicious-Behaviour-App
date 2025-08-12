"""
Enhanced file handling utilities for image processing
"""

import os
import logging
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class FileHandler:
    """Robust file handling with error recovery and validation"""
    
    @staticmethod
    def ensure_directory_exists(directory: str) -> bool:
        """Ensure directory exists and is writable"""
        try:
            os.makedirs(directory, exist_ok=True)
            return os.access(directory, os.W_OK)
        except Exception as e:
            logger.error(f"Failed to create/access directory {directory}: {e}")
            return False
    
    @staticmethod
    def validate_image_path(image_path: str) -> Tuple[bool, str]:
        """Validate if image file exists and is readable"""
        if not image_path:
            return False, "Empty path provided"
        
        if not os.path.exists(image_path):
            return False, f"File does not exist: {image_path}"
        
        if not os.path.isfile(image_path):
            return False, f"Path is not a file: {image_path}"
        
        if not os.access(image_path, os.R_OK):
            return False, f"File is not readable: {image_path}"
        
        # Check if it's a valid image file
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext not in valid_extensions:
            return False, f"Invalid image format: {file_ext}"
        
        return True, "Valid"
    
    @staticmethod
    def get_safe_filename(timestamp: str, extension: str = ".jpg") -> str:
        """Generate safe filename from timestamp"""
        try:
            # Clean timestamp for filename
            safe_timestamp = timestamp.replace(":", "-").replace(".", "-")
            return f"frame_{safe_timestamp}{extension}"
        except Exception as e:
            logger.error(f"Failed to generate safe filename: {e}")
            return f"frame_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
    
    @staticmethod
    def cleanup_old_files(directory: str, max_files: int = 1000) -> int:
        """Clean up old files to prevent directory bloat"""
        try:
            if not os.path.exists(directory):
                return 0
            
            files = [f for f in os.listdir(directory) if f.startswith('frame_')]
            files.sort(key=lambda x: os.path.getctime(os.path.join(directory, x)))
            
            deleted_count = 0
            while len(files) > max_files:
                oldest_file = files.pop(0)
                file_path = os.path.join(directory, oldest_file)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0
