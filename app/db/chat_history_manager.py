"""
MongoDB Chat History Manager for Suspicious Behavior Detection
Provides comprehensive MongoDB operations for chat history and behavior logs
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from bson import ObjectId
import uuid

logger = logging.getLogger(__name__)

class SuspiciousBehaviorChatHistoryManager:
    """
    Manages chat history and logs for suspicious behavior detection
    using MongoDB for persistent storage.
    """
    
    def __init__(self):
        self.connection_string = os.getenv(
            "MONGODB_CONNECTION_STRING", 
            os.getenv("MONGO_URI", "mongodb://localhost:27017")
        )
        self.database_name = os.getenv("MONGODB_DATABASE_NAME", "cash_counter")
        self.collection_name = "suspicious_behavior_chat_history"
        
        # Initialize MongoDB client
        self.client = MongoClient(self.connection_string)
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
        
    def create_chat_session(self, session_metadata: Dict[str, Any] = None) -> str:
        """Create a new chat session with metadata."""
        session_id = str(uuid.uuid4())
        
        # Store session metadata
        session_doc = {
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "metadata": session_metadata or {},
            "status": "active"
        }
        
        self.db.suspicious_behavior_sessions.insert_one(session_doc)
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a message to chat history."""
        message_doc = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        self.collection.insert_one(message_doc)
    
    def get_chat_history(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get chat history for a specific session."""
        return list(
            self.collection.find({"session_id": session_id})
            .sort("timestamp", -1)
            .limit(limit)
        )
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a chat session."""
        messages = self.get_chat_history(session_id)
        
        return {
            "session_id": session_id,
            "message_count": len(messages),
            "first_message": messages[-1] if messages else None,
            "last_message": messages[0] if messages else None,
            "created_at": messages[-1]["timestamp"] if messages else None
        }
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up old chat sessions."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Archive old messages
        old_messages = self.collection.delete_many({
            "timestamp": {"$lt": cutoff_date}
        })
        
        logger.info(f"Cleaned up {old_messages.deleted_count} old messages")
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active chat sessions."""
        return list(self.db.suspicious_behavior_sessions.find({"status": "active"}))
    
    def close_session(self, session_id: str):
        """Mark a chat session as closed."""
        self.db.suspicious_behavior_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "closed", "closed_at": datetime.utcnow()}}
        )
    
    def get_session_stats(self) -> Dict[str, int]:
        """Get statistics about chat sessions."""
        return {
            "total_sessions": self.db.suspicious_behavior_sessions.count_documents({}),
            "active_sessions": self.db.suspicious_behavior_sessions.count_documents({"status": "active"}),
            "total_messages": self.collection.count_documents({}),
            "messages_today": self.collection.count_documents({
                "timestamp": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            })
        }
    
    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
