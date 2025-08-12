"""
MongoDB Handler for Cash Counter Monitoring System
Provides comprehensive MongoDB operations with error handling and performance optimization
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, PyMongoError
from bson import ObjectId
import json

# Configure logging
logger = logging.getLogger(__name__)

class MongoDBHandler:
    """Enhanced MongoDB handler with comprehensive database operations"""
    
    def __init__(self, connection_string: Optional[str] = None):
        """Initialize MongoDB connection with comprehensive error handling"""
        try:
            # Use provided connection string or environment variable
            from app.db.mongo_config import MongoDBConfig
            self.connection_string = connection_string or MongoDBConfig.get_connection_string()
            
            # Initialize client with enhanced timeout settings
            client_options = MongoDBConfig.get_client_options()
            self.client = MongoClient(
                self.connection_string,
                **client_options
            )
            
            # Test connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Initialize database
            self.db = self.client["cash_counter"]
            
            # Initialize collections
            self.observations = self.db["observations"]
            self.telemetry = self.db["telemetry"]
            self.alerts = self.db["alerts"]
            self.system_health = self.db["system_health"]
            self.models = self.db["models"]
            self.performance_metrics = self.db["performance_metrics"]
            self.chat_history = self.db["chat_message_history"]
            
            # Create indexes for optimal performance
            self._create_indexes()
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Create comprehensive indexes for optimal query performance"""
        try:
            # Observations collection indexes
            self.observations.create_index([("timestamp", DESCENDING)])
            self.observations.create_index([("theft_detected", ASCENDING)])
            self.observations.create_index([("eval_result", ASCENDING)])
            self.observations.create_index([("human_feedback", ASCENDING)])
            self.observations.create_index([("image_path", ASCENDING)])
            self.observations.create_index([("timestamp", DESCENDING), ("theft_detected", ASCENDING)])
            
            # Telemetry collection indexes
            self.telemetry.create_index([("timestamp", DESCENDING)])
            self.telemetry.create_index([("metric_type", ASCENDING)])
            self.telemetry.create_index([("timestamp", DESCENDING), ("metric_type", ASCENDING)])
            
            # Alerts collection indexes
            self.alerts.create_index([("timestamp", DESCENDING)])
            self.alerts.create_index([("alert_type", ASCENDING)])
            self.alerts.create_index([("severity", ASCENDING)])
            self.alerts.create_index([("resolved", ASCENDING)])
            
            # System health indexes
            self.system_health.create_index([("timestamp", DESCENDING)])
            
            # Models collection indexes
            self.models.create_index([("name", ASCENDING), ("version", ASCENDING)])
            self.models.create_index([("timestamp", DESCENDING)])
            
            # Performance metrics indexes
            self.performance_metrics.create_index([("timestamp", DESCENDING)])
            
            logger.info("MongoDB indexes created successfully")
            
        except PyMongoError as e:
            logger.error(f"Error creating indexes: {e}")
            raise
    
    def save_observation(self, data: Dict[str, Any]) -> str:
        """Save observation with comprehensive error handling"""
        try:
            # Ensure timestamp is properly formatted
            if 'timestamp' not in data:
                data['timestamp'] = datetime.utcnow()
            elif isinstance(data['timestamp'], str):
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            
            # Insert observation
            result = self.observations.insert_one(data)
            logger.info(f"Observation saved with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Failed to save observation: {e}")
            raise
    
    def get_observations(self, limit: int = 100, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get observations with flexible filtering and pagination"""
        try:
            query = filter_dict or {}
            cursor = self.observations.find(query).sort("timestamp", DESCENDING).limit(limit)
            
            observations = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc['_id'] = str(doc['_id'])
                observations.append(doc)
            
            return observations
            
        except PyMongoError as e:
            logger.error(f"Failed to get observations: {e}")
            return []
    
    def get_observations_with_aggregation(self, pipeline: List[Dict]) -> List[Dict[str, Any]]:
        """Advanced observations retrieval using MongoDB aggregation pipeline"""
        try:
            results = list(self.observations.aggregate(pipeline))
            # Convert ObjectId to string
            for result in results:
                if '_id' in result and isinstance(result['_id'], ObjectId):
                    result['_id'] = str(result['_id'])
            return results
        except PyMongoError as e:
            logger.error(f"Aggregation failed: {e}")
            return []
    
    def save_telemetry(self, data: Dict[str, Any]) -> str:
        """Save telemetry data with automatic timestamp"""
        try:
            if 'timestamp' not in data:
                data['timestamp'] = datetime.utcnow()
            elif isinstance(data['timestamp'], str):
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            
            result = self.telemetry.insert_one(data)
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Failed to save telemetry: {e}")
            raise
    
    def register_model(self, model_name: str, version: str, metadata: Dict[str, Any]) -> str:
        """Register model with version tracking"""
        try:
            model_data = {
                "name": model_name,
                "version": version,
                "metadata": metadata,
                "timestamp": datetime.utcnow()
            }
            
            result = self.models.insert_one(model_data)
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Failed to register model: {e}")
            raise
    
    def save_alert(self, alert_type: str, severity: str, data: Dict[str, Any]) -> str:
        """Save alert with comprehensive metadata"""
        try:
            alert_data = {
                "alert_type": alert_type,
                "severity": severity,
                "data": data,
                "timestamp": datetime.utcnow(),
                "resolved": False
            }
            
            result = self.alerts.insert_one(alert_data)
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Failed to save alert: {e}")
            raise
    
    def get_alerts(self, limit: int = 50, resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get alerts with filtering options"""
        try:
            query = {}
            if resolved is not None:
                query['resolved'] = resolved
            
            cursor = self.alerts.find(query).sort("timestamp", DESCENDING).limit(limit)
            
            alerts = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                alerts.append(doc)
            
            return alerts
            
        except PyMongoError as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
    
    def update_observation(self, observation_id: str, update_data: Dict[str, Any]) -> bool:
        """Update existing observation"""
        try:
            result = self.observations.update_one(
                {"_id": ObjectId(observation_id)},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Updated observation {observation_id}")
                return True
            return False
            
        except PyMongoError as e:
            logger.error(f"Failed to update observation: {e}")
            return False
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary using MongoDB aggregation"""
        try:
            cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
            
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": datetime.fromtimestamp(cutoff_time)}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_observations": {"$sum": 1},
                        "avg_latency": {"$avg": "$latency_ms"},
                        "total_cost": {"$sum": "$cost_usd"},
                        "theft_detections": {
                            "$sum": {
                                "$cond": [{"$eq": ["$theft_detected", True]}, 1, 0]
                            }
                        },
                        "correct_evaluations": {
                            "$sum": {
                                "$cond": [{"$eq": ["$eval_result", "CORRECT"]}, 1, 0]
                            }
                        }
                    }
                }
            ]
            
            results = list(self.observations.aggregate(pipeline))
            return results[0] if results else {}
            
        except PyMongoError as e:
            logger.error(f"Failed to get performance summary: {e}")
            return {}
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        try:
            # Get recent system health data
            recent_health = list(
                self.system_health.find()
                .sort("timestamp", DESCENDING)
                .limit(1)
            )
            
            if recent_health:
                recent_health[0]['_id'] = str(recent_health[0]['_id'])
                return recent_health[0]
            
            return {}
            
        except PyMongoError as e:
            logger.error(f"Failed to get system health: {e}")
            return {}
    
    def close(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            logger.info("MongoDB connection closed")
        except PyMongoError as e:
            logger.error(f"Error closing MongoDB connection: {e}")
    
    def health_check(self) -> bool:
        """Check MongoDB connection health"""
        try:
            self.client.admin.command('ping')
            return True
        except PyMongoError:
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            collection = self.db[collection_name]
            stats = self.db.command("collStats", collection_name)
            return {
                "document_count": stats.get("count", 0),
                "size": stats.get("size", 0),
                "avg_obj_size": stats.get("avgObjSize", 0),
                "storage_size": stats.get("storageSize", 0)
            }
        except PyMongoError as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}

# Global MongoDB handler instance
_mongo_handler = None

def get_mongo_handler():
    """Get or create global MongoDB handler"""
    global _mongo_handler
    if _mongo_handler is None:
        _mongo_handler = MongoDBHandler()
    return _mongo_handler
