"""
MongoDB Chat History Manager using LangChain MongoDB integration
for suspicious behavior detection logs and chat histories.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from pymongo import MongoClient
from bson import ObjectId
import uuid

logger = logging.getLogger(__name__)

class SuspiciousBehaviorChatHistoryManager:
    """
    Manages chat history and logs for suspicious behavior detection
    using MongoDBChatMessageHistory from LangChain.
    """
    
    def __init__(self):
        self.connection_string = os.getenv(
            "MONGODB_CONNECTION_STRING", 
            os.getenv("MONGO_URI", "mongodb://localhost:27017")
        )
        self.database_name = os.getenv("MONGODB_DATABASE_NAME", "cash_counter")
        self.collection_name = os.getenv("MONGODB_COLLECTION_NAME", "suspicious_behavior_chat_history")
        
        # Initialize MongoDB client
        self.client = MongoClient(self.connection_string)
        self.db = self.client[self.database_name]
        
    def create_session(self, session_metadata: Dict[str, Any] = None) -> str:
        """Create a new session with metadata."""
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
    
    def get_chat_history(self, session_id: str) -> MongoDBChatMessageHistory:
        """Get chat history for a specific session."""
        return MongoDBChatMessageHistory(
            session_id=session_id,
            connection_string=self.connection_string,
            database_name=self.database_name,
            collection_name=self.collection_name
        )
    
    def log_detection_event(self, session_id: str, detection_data: Dict[str, Any]):
        """Log a suspicious behavior detection event."""
        event_doc = {
            "session_id": session_id,
            "timestamp": datetime.utcnow(),
            "event_type": "detection",
            "detection_data": detection_data,
            "source": "suspicious_behavior_detector"
        }
        
        self.db.suspicious_behavior_events.insert_one(event_doc)
        
        # Also log as a system message in chat history
        chat_history = self.get_chat_history(session_id)
        system_message = f"Suspicious behavior detected: {detection_data.get('description', 'Unknown')}"
        chat_history.add_message({"role": "system", "content": system_message})
    
    def log_user_feedback(self, session_id: str, feedback: str, user_id: str = None):
        """Log user feedback for a detection."""
        feedback_doc = {
            "session_id": session_id,
            "timestamp": datetime.utcnow(),
            "event_type": "user_feedback",
            "feedback": feedback,
            "user_id": user_id or "anonymous"
        }
        
        self.db.suspicious_behavior_feedback.insert_one(feedback_doc)
        
        # Add to chat history
        chat_history = self.get_chat_history(session_id)
        chat_history.add_message({"role": "user", "content": f"Feedback: {feedback}"})
    
    def get_session_history(self, session_id: str) -> Dict[str, Any]:
        """Get complete session history including detections and feedback."""
        chat_history = self.get_chat_history(session_id)
        messages = chat_history.messages
        
        # Get detection events
        detections = list(self.db.suspicious_behavior_events.find(
            {"session_id": session_id, "event_type": "detection"}
        ).sort("timestamp", 1))
        
        # Get feedback
        feedback = list(self.db.suspicious_behavior_feedback.find(
            {"session_id": session_id}
        ).sort("timestamp", 1))
        
        return {
            "messages": messages,
            "detections": detections,
            "feedback": feedback
        }
    
    def close_session(self, session_id: str):
        """Mark a session as closed."""
        self.db.suspicious_behavior_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "closed", "closed_at": datetime.utcnow()}}
        )
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions."""
        return list(self.db.suspicious_behavior_sessions.find({"status": "active"}))
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up sessions older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        # Close old sessions
        old_sessions = list(self.db.suspicious_behavior_sessions.find(
            {"created_at": {"$lt": cutoff_date}, "status": "active"}
        ))
        
        for session in old_sessions:
            self.close_session(session["session_id"])
        
        logger.info(f"Cleaned up {len(old_sessions)} old sessions")
    
    def get_migration_handler(self):
        """Get migration handler instance."""
        return self

if __name__ == "__main__":
    # Run migration when script is executed directly
    manager = SuspiciousBehaviorChatHistoryManager()
    manager.cleanup_old_sessions()
