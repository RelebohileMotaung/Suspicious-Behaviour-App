"""
Database Migration Utilities for MongoDB Integration

This module provides utilities for managing database migrations and schema updates
for the MongoDB integration in production environments.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MongoDBMigration:
    """Handles database migrations and schema updates for MongoDB."""
    
    def __init__(self, connection_string=None):
        """Initialize migration handler with MongoDB connection."""
        from app.db.mongo_config import MongoDBConfig
        
        self.connection_string = connection_string or MongoDBConfig.get_connection_string()
        self.client = None
        self.db = None
        
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client.get_database()
            # Verify connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB for migration")
            return True
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
            
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
            
    def create_indexes(self):
        """Create necessary indexes for optimal performance."""
        try:
            if not self.connect():
                return False
                
            # Create indexes for observations collection
            observations = self.db.observations
            observations.create_index([("timestamp", -1)])
            observations.create_index([("theft_detected", 1)])
            observations.create_index([("observation_id", 1)], unique=True)
            
            # Create indexes for telemetry collection
            telemetry = self.db.telemetry
            telemetry.create_index([("timestamp", -1)])
            telemetry.create_index([("device_id", 1)])
            
            # Create indexes for alerts collection
            alerts = self.db.alerts
            alerts.create_index([("timestamp", -1)])
            alerts.create_index([("severity", 1)])
            alerts.create_index([("event_type", 1)])
            
            logger.info("Successfully created all necessary indexes")
            return True
            
        except PyMongoError as e:
            logger.error(f"Error creating indexes: {e}")
            return False
        finally:
            self.disconnect()
            
    def validate_schema(self):
        """Validate existing collections and schema."""
        try:
            if not self.connect():
                return False
                
            collections = self.db.list_collection_names()
            required_collections = ['observations', 'telemetry', 'alerts', 'chat_history']
            
            missing_collections = [col for col in required_collections if col not in collections]
            if missing_collections:
                logger.warning(f"Missing collections: {missing_collections}")
                return False
                
            logger.info("All required collections exist")
            return True
            
        except PyMongoError as e:
            logger.error(f"Error validating schema: {e}")
            return False
        finally:
            self.disconnect()
            
    def migrate_data(self, source_collection, target_collection, transformation_func=None):
        """Migrate data between collections with optional transformation."""
        try:
            if not self.connect():
                return False
                
            source = self.db[source_collection]
            target = self.db[target_collection]
            
            documents = source.find()
            migrated_count = 0
            
            for doc in documents:
                if transformation_func:
                    doc = transformation_func(doc)
                    
                target.insert_one(doc)
                migrated_count += 1
                
            logger.info(f"Migrated {migrated_count} documents from {source_collection} to {target_collection}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Error migrating data: {e}")
            return False
        finally:
            self.disconnect()
            
    def backup_collection(self, collection_name, backup_suffix=None):
        """Create backup of a collection."""
        try:
            if not self.connect():
                return False
                
            source = self.db[collection_name]
            backup_name = f"{collection_name}_backup_{backup_suffix or datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup = self.db[backup_name]
            
            documents = list(source.find())
            if documents:
                backup.insert_many(documents)
                logger.info(f"Backed up {len(documents)} documents from {collection_name} to {backup_name}")
            else:
                logger.info(f"No documents to backup in {collection_name}")
                
            return True
            
        except PyMongoError as e:
            logger.error(f"Error backing up collection: {e}")
            return False
        finally:
            self.disconnect()
            
    def run_migration(self):
        """Run complete migration process."""
        logger.info("Starting MongoDB migration process...")
        
        # Create indexes
        if not self.create_indexes():
            return False
            
        # Validate schema
        if not self.validate_schema():
            return False
            
        logger.info("Migration process completed successfully")
        return True


def get_migration_handler():
    """Get migration handler instance."""
    return MongoDBMigration()


if __name__ == "__main__":
    # Run migration when script is executed directly
    migration = get_migration_handler()
    migration.run_migration()
