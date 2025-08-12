"""
MongoDB Configuration for Enhanced Connection Management
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MongoDBConfig:
    """Enhanced MongoDB configuration with improved timeout settings"""
    
    @staticmethod
    def get_connection_string() -> str:
        """Get MongoDB connection string from environment variables"""
        return os.getenv(
            "MONGO_URI",
            os.getenv("MONGODB_CONNECTION_STRING", "mongodb://localhost:27017")
        )
    
    @staticmethod
    def get_client_options() -> dict:
        """Get MongoDB client options with enhanced timeout settings"""
        return {
            "maxPoolSize": 50,
            "minPoolSize": 10,
            "maxIdleTimeMS": 45000,
            "serverSelectionTimeoutMS": 10000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 30000,
            "retryWrites": True,
            "retryReads": True,
            "w": "majority",
            "readPreference": "primaryPreferred"
        }
