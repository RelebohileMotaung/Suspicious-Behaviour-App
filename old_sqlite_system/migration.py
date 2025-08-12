"""
Data Migration Script: SQLite to MongoDB
Handles comprehensive data migration with error handling and validation
"""

import sqlite3
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from bson import ObjectId

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigrator:
    """Comprehensive SQLite to MongoDB data migrator"""
    
    def __init__(self, sqlite_db_path: str, mongo_handler):
        self.sqlite_db_path = sqlite_db_path
        self.mongo = mongo_handler
    
    def migrate_observations(self) -> Dict[str, int]:
        """Migrate observations from SQLite to MongoDB"""
        try:
            conn = sqlite3.connect(self.sqlite_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get all observations
            cursor.execute("SELECT * FROM observations ORDER BY id")
            rows = cursor.fetchall()
            
            migrated_count = 0
            skipped_count = 0
            
            for row in rows:
                try:
                    # Convert SQLite row to MongoDB document
                    doc = {
                        "_id": ObjectId(),  # Generate new MongoDB ObjectId
                        "timestamp": self._parse_timestamp(row['timestamp']),
                        "observation": row['observation'],
                        "image_path": row['image_path'],
                        "latency_ms": float(row['latency_ms']) if row['latency_ms'] is not None else 0.0,
                        "tokens_in": int(row['tokens_in']) if row['tokens_in'] is not None else 0,
                        "tokens_out": int(row['tokens_out']) if row['tokens_out'] is not None else 0,
                        "cost_usd": float(row['cost_usd']) if row['cost_usd'] is not None else 0.0,
                        "theft_detected": bool(row['theft_detected']) if row['theft_detected'] is not None else False,
                        "eval_result": row['eval_result'],
                        "human_feedback": row['human_feedback'],
                        "model_version": row['model_version'],
                        "migrated_from": "sqlite",
                        "migration_date": datetime.utcnow()
                    }
                    
                    # Insert into MongoDB
                    self.mongo.observations.insert_one(doc)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate observation {row['id']}: {e}")
                    skipped_count += 1
            
            conn.close()
            
            logger.info(f"Observations migration completed: {migrated_count} migrated, {skipped_count} skipped")
            return {"migrated": migrated_count, "skipped": skipped_count}
            
        except Exception as e:
            logger.error(f"Observations migration failed: {e}")
            return {"migrated": 0, "skipped": 0}
    
    def migrate_telemetry(self) -> Dict[str, int]:
        """Migrate telemetry data from telemetry_manager.db"""
        try:
            telemetry_db_path = "telemetry/telemetry_manager.db"
            if not os.path.exists(telemetry_db_path):
                logger.info("Telemetry database not found, skipping telemetry migration")
                return {"migrated": 0, "skipped": 0}
            
            conn = sqlite3.connect(telemetry_db_path)
            conn.row_factory = sqlite3.Row
            
            # Migrate metrics
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM metrics ORDER BY id")
            metrics_rows = cursor.fetchall()
            
            migrated_metrics = 0
            skipped_metrics = 0
            
            for row in metrics_rows:
                try:
                    doc = {
                        "timestamp": datetime.fromtimestamp(row['timestamp']),
                        "metric_type": row['metric_type'],
                        "value": float(row['value']),
                        "metadata": json.loads(row['metadata']) if row['metadata'] else {},
                        "migrated_from": "sqlite",
                        "migration_date": datetime.utcnow()
                    }
                    
                    self.mongo.telemetry.insert_one(doc)
                    migrated_metrics += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate metric {row['id']}: {e}")
                    skipped_metrics += 1
            
            # Migrate alerts
            cursor.execute("SELECT * FROM alerts ORDER BY id")
            alerts_rows = cursor.fetchall()
            
            migrated_alerts = 0
            skipped_alerts = 0
            
            for row in alerts_rows:
                try:
                    doc = {
                        "timestamp": datetime.fromtimestamp(row['timestamp']),
                        "alert_type": row['alert_type'],
                        "severity": row['severity'],
                        "data": json.loads(row['data']) if row['data'] else {},
                        "resolved": bool(row['resolved']),
                        "migrated_from": "sqlite",
                        "migration_date": datetime.utcnow()
                    }
                    
                    self.mongo.alerts.insert_one(doc)
                    migrated_alerts += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate alert {row['id']}: {e}")
                    skipped_alerts += 1
            
            conn.close()
            
            logger.info(f"Telemetry migration completed: {migrated_metrics} metrics, {migrated_alerts} alerts")
            return {
                "metrics_migrated": migrated_metrics,
                "metrics_skipped": skipped_metrics,
                "alerts_migrated": migrated_alerts,
                "alerts_skipped": skipped_alerts
            }
            
        except Exception as e:
            logger.error(f"Telemetry migration failed: {e}")
            return {"metrics_migrated": 0, "metrics_skipped": 0, "alerts_migrated": 0, "alerts_skipped": 0}
    
    def migrate_system_health(self) -> Dict[str, int]:
        """Migrate system health data"""
        try:
            telemetry_db_path = "telemetry/telemetry_manager.db"
            if not os.path.exists(telemetry_db_path):
                return {"migrated": 0, "skipped": 0}
            
            conn = sqlite3.connect(telemetry_db_path)
            conn.row_factory = sqlite3.Row
            
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_health ORDER BY id")
            rows = cursor.fetchall()
            
            migrated_count = 0
            skipped_count = 0
            
            for row in rows:
                try:
                    doc = {
                        "timestamp": datetime.fromtimestamp(row['timestamp']),
                        "cpu_usage": float(row['cpu_usage']) if row['cpu_usage'] is not None else 0.0,
                        "memory_usage": float(row['memory_usage']) if row['memory_usage'] is not None else 0.0,
                        "disk_usage": float(row['disk_usage']) if row['disk_usage'] is not None else 0.0,
                        "active_alerts": int(row['active_alerts']) if row['active_alerts'] is not None else 0,
                        "migrated_from": "sqlite",
                        "migration_date": datetime.utcnow()
                    }
                    
                    self.mongo.system_health.insert_one(doc)
                    migrated_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to migrate system health {row['id']}: {e}")
                    skipped_count += 1
            
            conn.close()
            
            logger.info(f"System health migration completed: {migrated_count} migrated, {skipped_count} skipped")
            return {"migrated": migrated_count, "skipped": skipped_count}
            
        except Exception as e:
            logger.error(f"System health migration failed: {e}")
            return {"migrated": 0, "skipped": 0}
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse various timestamp formats to datetime"""
        try:
            if timestamp_str is None:
                return datetime.utcnow()
            
            # Handle different timestamp formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d_%H-%M-%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(str(timestamp_str), fmt)
                except ValueError:
                    continue
            
            # If all formats fail, return current time
            logger.warning(f"Could not parse timestamp: {timestamp_str}, using current time")
            return datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error parsing timestamp: {e}")
            return datetime.utcnow()
    
    def validate_migration(self) -> Dict[str, Any]:
        """Validate migration results"""
        try:
            # Count documents in MongoDB
            observations_count = self.mongo.observations.count_documents({})
            telemetry_count = self.mongo.telemetry.count_documents({})
            alerts_count = self.mongo.alerts.count_documents({})
            system_health_count = self.mongo.system_health.count_documents({})
            
            # Count documents in SQLite
            conn = sqlite3.connect(self.sqlite_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM observations")
            sqlite_observations = cursor.fetchone()[0]
            
            conn.close()
            
            # Check telemetry database
            telemetry_db_path = "telemetry/telemetry_manager.db"
            sqlite_telemetry = 0
            sqlite_alerts = 0
            sqlite_system_health = 0
            
            if os.path.exists(telemetry_db_path):
                conn = sqlite3.connect(telemetry_db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM metrics")
                sqlite_telemetry = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM alerts")
                sqlite_alerts = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM system_health")
                sqlite_system_health = cursor.fetchone()[0]
                
                conn.close()
            
            return {
                "observations": {
                    "sqlite": sqlite_observations,
                    "mongodb": observations_count
                },
                "telemetry": {
                    "sqlite": sqlite_telemetry,
                    "mongodb": telemetry_count
                },
                "alerts": {
                    "sqlite": sqlite_alerts,
                    "mongodb": alerts_count
                },
                "system_health": {
                    "sqlite": sqlite_system_health,
                    "mongodb": system_health_count
                }
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {"error": str(e)}
    
    def run_full_migration(self) -> Dict[str, Any]:
        """Run complete migration process"""
        logger.info("Starting full migration from SQLite to MongoDB")
        
        results = {
            "observations": self.migrate_observations(),
            "telemetry": self.migrate_telemetry(),
            "system_health": self.migrate_system_health(),
            "validation": self.validate_migration()
        }
        
        logger.info("Migration completed")
        return results

def main():
    """Main migration function"""
    try:
        # Import MongoDB handler
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from app.db.mongo_handler import get_mongo_handler
        
        # Initialize migrator
        mongo_handler = get_mongo_handler()
        migrator = DataMigrator("robust_telemetry.db", mongo_handler)
        
        # Run migration
        results = migrator.run_full_migration()
        
        # Print results
        print("Migration Results:")
        print(json.dumps(results, indent=2, default=str))
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
