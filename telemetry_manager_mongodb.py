"""
Enhanced Telemetry Manager with MongoDB Integration
Provides comprehensive telemetry collection and monitoring with MongoDB backend
"""

import json
import time
import logging
import threading
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass, asdict

# Import MongoDB handler
from app.db.mongo_handler import get_mongo_handler

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Structured alert data"""
    timestamp: float
    alert_type: str
    severity: str
    data: Dict[str, Any]
    resolved: bool = False

class TelemetryManagerMongoDB:
    """Enhanced telemetry manager with MongoDB integration and real-time monitoring"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize telemetry manager with MongoDB backend"""
        self.config = self._load_config(config_path)
        self.alert_thresholds = self.config.get('thresholds', {
            'latency': 3000,  # ms
            'cost': 0.005,    # USD
            'error_rate': 0.1, # 10%
            'cpu_usage': 80,  # %
            'memory_usage': 85  # %
        })
        
        self.metrics = {
            'error_count': 0,
            'total_operations': 0,
            'total_latency': 0,
            'total_cost': 0.0,
            'start_time': time.time()
        }
        
        self.alerts: List[Alert] = []
        self.lock = threading.Lock()
        
        # Initialize MongoDB handler
        self.mongo = get_mongo_handler()
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
        return {}
    
    def record_metric(self, metric_type: str, value: float, metadata: Optional[Dict] = None) -> str:
        """Record a metric to MongoDB"""
        try:
            metric_data = {
                "metric_type": metric_type,
                "value": float(value),
                "metadata": metadata or {},
                "timestamp": datetime.utcnow()
            }
            
            metric_id = self.mongo.save_telemetry(metric_data)
            logger.debug(f"Metric recorded: {metric_type}={value}")
            return metric_id
            
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
            return ""
    
    def record_operation(self, latency_ms: float, cost_usd: float = 0.0, success: bool = True) -> None:
        """Record operation metrics with MongoDB storage"""
        with self.lock:
            self.metrics['total_operations'] += 1
            self.metrics['total_latency'] += latency_ms
            self.metrics['total_cost'] += cost_usd
            
            if not success:
                self.metrics['error_count'] += 1
                self.record_error()
            
            # Record individual metrics to MongoDB
            self.record_metric('latency', latency_ms)
            if cost_usd > 0:
                self.record_metric('cost', cost_usd)
            
            # Check alert conditions
            self._check_alert_conditions({
                'latency_ms': latency_ms,
                'cost_usd': cost_usd,
                'success': success
            })
    
    def record_error(self, error_type: str = "general", details: Optional[Dict] = None) -> None:
        """Record error with context to MongoDB"""
        with self.lock:
            self.metrics['error_count'] += 1
            error_data = {
                'error_type': error_type,
                'details': details or {},
                'total_errors': self.metrics['error_count']
            }
            self.record_metric('error', 1, error_data)
            
            # Check error rate
            error_rate = self.metrics['error_count'] / max(1, self.metrics['total_operations'])
            if error_rate > self.alert_thresholds['error_rate']:
                self.send_alert('high_error_rate', {
                    'error_rate': error_rate,
                    'total_errors': self.metrics['error_count'],
                    'total_operations': self.metrics['total_operations']
                })
    
    def _check_alert_conditions(self, metrics: Dict) -> None:
        """Check if metrics exceed thresholds"""
        alerts = []
        
        if metrics.get('latency_ms', 0) > self.alert_thresholds['latency']:
            alerts.append(('high_latency', metrics['latency_ms']))
        
        if metrics.get('cost_usd', 0) > self.alert_thresholds['cost']:
            alerts.append(('high_cost', metrics['cost_usd']))
        
        for alert_type, value in alerts:
            self.send_alert(alert_type, {'value': value, 'threshold': self.alert_thresholds[alert_type]})
    
    def send_alert(self, alert_type: str, data: Dict) -> None:
        """Send alert with enhanced routing and MongoDB storage"""
        with self.lock:
            # Determine severity
            severity_map = {
                'high_error_rate': 'critical',
                'critical_failure': 'critical',
                'high_latency': 'warning',
                'high_cost': 'warning'
            }
            severity = severity_map.get(alert_type, 'info')
            
            alert = Alert(
                timestamp=time.time(),
                alert_type=alert_type,
                severity=severity,
                data=data
            )
            
            self.alerts.append(alert)
            
            # Save to MongoDB
            try:
                alert_id = self.mongo.save_alert(alert_type, severity, data)
                logger.info(f"Alert saved to MongoDB: {alert_id}")
            except Exception as e:
                logger.error(f"Failed to save alert to MongoDB: {e}")
            
            # Log alert
            logger.warning(f"ALERT [{severity.upper()}] {alert_type}: {data}")
            
            # Send to webhook if configured
            webhook_url = os.getenv("ALERT_WEBHOOK")
            if webhook_url:
                try:
                    requests.post(webhook_url, json=asdict(alert), timeout=2)
                except Exception as e:
                    logger.error(f"Failed to send webhook alert: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        with self.lock:
            uptime = time.time() - self.metrics['start_time']
            error_rate = self.metrics['error_count'] / max(1, self.metrics['total_operations'])
            avg_latency = self.metrics['total_latency'] / max(1, self.metrics['total_operations'])
            
            health_data = {
                'uptime_seconds': uptime,
                'total_operations': self.metrics['total_operations'],
                'error_count': self.metrics['error_count'],
                'error_rate': error_rate,
                'avg_latency_ms': avg_latency,
                'total_cost_usd': self.metrics['total_cost'],
                'active_alerts': len([a for a in self.alerts if not a.resolved]),
                'timestamp': datetime.utcnow()
            }
            
            # Save system health to MongoDB
            try:
                self.mongo.system_health.insert_one(health_data)
            except Exception as e:
                logger.error(f"Failed to save system health: {e}")
            
            return health_data
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts from MongoDB"""
        try:
            return self.mongo.get_alerts(limit=limit)
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for specified time period from MongoDB"""
        try:
            # Use MongoDB aggregation for comprehensive metrics
            cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
            
            # Get metrics summary
            metrics_data = self.mongo.telemetry.find({
                "timestamp": {"$gte": datetime.fromtimestamp(cutoff_time)}
            })
            
            metrics_summary = {}
            for metric in metrics_data:
                metric_type = metric.get('metric_type')
                if metric_type not in metrics_summary:
                    metrics_summary[metric_type] = {
                        'count': 0,
                        'sum': 0.0,
                        'avg': 0.0,
                        'min': float('inf'),
                        'max': float('-inf')
                    }
                
                value = metric.get('value', 0.0)
                metrics_summary[metric_type]['count'] += 1
                metrics_summary[metric_type]['sum'] += value
                metrics_summary[metric_type]['min'] = min(metrics_summary[metric_type]['min'], value)
                metrics_summary[metric_type]['max'] = max(metrics_summary[metric_type]['max'], value)
            
            # Calculate averages
            for metric_type in metrics_summary:
                count = metrics_summary[metric_type]['count']
                if count > 0:
                    metrics_summary[metric_type]['avg'] = metrics_summary[metric_type]['sum'] / count
            
            # Get alerts summary
            alerts_data = self.mongo.alerts.find({
                "timestamp": {"$gte": datetime.fromtimestamp(cutoff_time)}
            })
            
            alerts_summary = {}
            for alert in alerts_data:
                severity = alert.get('severity', 'info')
                alerts_summary[severity] = alerts_summary.get(severity, 0) + 1
            
            return {
                'metrics': metrics_summary,
                'alerts': alerts_summary,
                'time_range_hours': hours,
                'total_records': sum(m['count'] for m in metrics_summary.values())
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {}
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends using MongoDB aggregation"""
        try:
            cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
            
            # Use MongoDB aggregation for performance trends
            pipeline = [
                {
                    "$match": {
                        "timestamp": {"$gte": datetime.fromtimestamp(cutoff_time)}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "year": {"$year": "$timestamp"},
                            "month": {"$month": "$timestamp"},
                            "day": {"$dayOfMonth": "$timestamp"},
                            "hour": {"$hour": "$timestamp"}
                        },
                        "avg_latency": {"$avg": "$value"},
                        "total_cost": {"$sum": {"$cond": [{"$eq": ["$metric_type", "cost"]}, "$value", 0]}},
                        "error_count": {"$sum": {"$cond": [{"$eq": ["$metric_type", "error"]}, 1, 0]}},
                        "operation_count": {"$sum": {"$cond": [{"$eq": ["$metric_type", "latency"]}, 1, 0]}}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            trends = list(self.mongo.telemetry.aggregate(pipeline))
            return {
                'trends': trends,
                'hours': hours
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return {}

# Global telemetry manager instance
_telemetry_manager_mongodb = None

def get_telemetry_manager_mongodb():
    """Get or create global telemetry manager with MongoDB"""
    global _telemetry_manager_mongodb
    if _telemetry_manager_mongodb is None:
        _telemetry_manager_mongodb = TelemetryManagerMongoDB()
    return _telemetry_manager_mongodb
