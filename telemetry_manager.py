import json
import time
import logging
import threading
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dataclasses import dataclass, asdict

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

class TelemetryManager:
    """Enhanced telemetry manager with database integration and real-time monitoring"""
    
    def __init__(self, config_path: Optional[str] = None):
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
        self.db_path = Path("telemetry/telemetry_manager.db")
        self._init_database()
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or use defaults"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _init_database(self):
        """Initialize telemetry database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    metric_type TEXT,
                    value REAL,
                    metadata TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    alert_type TEXT,
                    severity TEXT,
                    data TEXT,
                    resolved BOOLEAN DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    disk_usage REAL,
                    active_alerts INTEGER
                )
            ''')
    
    def record_metric(self, metric_type: str, value: float, metadata: Optional[Dict] = None):
        """Record a metric to database"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO metrics (timestamp, metric_type, value, metadata) VALUES (?, ?, ?, ?)",
                    (time.time(), metric_type, value, json.dumps(metadata or {}))
                )
    
    def record_operation(self, latency_ms: float, cost_usd: float = 0.0, success: bool = True):
        """Record operation metrics"""
        with self.lock:
            self.metrics['total_operations'] += 1
            self.metrics['total_latency'] += latency_ms
            self.metrics['total_cost'] += cost_usd
            
            if not success:
                self.metrics['error_count'] += 1
                self.record_error()
            
            # Record individual metrics
            self.record_metric('latency', latency_ms)
            if cost_usd > 0:
                self.record_metric('cost', cost_usd)
            
            # Check alert conditions
            self._check_alert_conditions({
                'latency_ms': latency_ms,
                'cost_usd': cost_usd,
                'success': success
            })
    
    def record_error(self, error_type: str = "general", details: Optional[Dict] = None):
        """Record error with context"""
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
    
    def _check_alert_conditions(self, metrics: Dict):
        """Check if metrics exceed thresholds"""
        alerts = []
        
        if metrics.get('latency_ms', 0) > self.alert_thresholds['latency']:
            alerts.append(('high_latency', metrics['latency_ms']))
        
        if metrics.get('cost_usd', 0) > self.alert_thresholds['cost']:
            alerts.append(('high_cost', metrics['cost_usd']))
        
        for alert_type, value in alerts:
            self.send_alert(alert_type, {'value': value, 'threshold': self.alert_thresholds[alert_type]})
    
    def send_alert(self, alert_type: str, data: Dict):
        """Send alert with enhanced routing"""
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
            
            # Persist to database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO alerts (timestamp, alert_type, severity, data) VALUES (?, ?, ?, ?)",
                    (alert.timestamp, alert.alert_type, alert.severity, json.dumps(alert.data))
                )
            
            # Log alert
            logger.warning(f"ALERT [{severity.upper()}] {alert_type}: {data}")
            
            # Send to webhook if configured
            webhook_url = os.getenv("ALERT_WEBHOOK")
            if webhook_url:
                try:
                    requests.post(webhook_url, json=asdict(alert), timeout=2)
                except Exception as e:
                    logger.error(f"Failed to send webhook alert: {e}")
    
    def get_system_health(self) -> Dict:
        """Get current system health metrics"""
        with self.lock:
            uptime = time.time() - self.metrics['start_time']
            error_rate = self.metrics['error_count'] / max(1, self.metrics['total_operations'])
            avg_latency = self.metrics['total_latency'] / max(1, self.metrics['total_operations'])
            
            return {
                'uptime_seconds': uptime,
                'total_operations': self.metrics['total_operations'],
                'error_count': self.metrics['error_count'],
                'error_rate': error_rate,
                'avg_latency_ms': avg_latency,
                'total_cost_usd': self.metrics['total_cost'],
                'active_alerts': len([a for a in self.alerts if not a.resolved])
            }
    
    def get_recent_alerts(self, limit: int = 10) -> List[Dict]:
        """Get recent alerts"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_metrics_summary(self, hours: int = 24) -> Dict:
        """Get metrics summary for specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get metrics
            cursor = conn.execute(
                "SELECT metric_type, AVG(value), COUNT(*) FROM metrics WHERE timestamp > ? GROUP BY metric_type",
                (cutoff_time,)
            )
            metrics_summary = {row[0]: {'avg': row[1], 'count': row[2]} for row in cursor.fetchall()}
            
            # Get alerts
            cursor = conn.execute(
                "SELECT severity, COUNT(*) FROM alerts WHERE timestamp > ? GROUP BY severity",
                (cutoff_time,)
            )
            alerts_summary = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'metrics': metrics_summary,
                'alerts': alerts_summary,
                'time_range_hours': hours
            }

# Global telemetry manager instance
telemetry_manager = None

def get_telemetry_manager():
    """Get or create global telemetry manager"""
    global telemetry_manager
    if telemetry_manager is None:
        telemetry_manager = TelemetryManager()
    return telemetry_manager
