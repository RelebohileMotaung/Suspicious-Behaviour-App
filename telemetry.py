import json
import time
import os
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Optional

# Configure telemetry directory
TELEMETRY_DIR = Path("telemetry")
TELEMETRY_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    filename=TELEMETRY_DIR / "app_telemetry.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Telemetry file paths
TELEMETRY_EVENTS_FILE = TELEMETRY_DIR / "events.jsonl"
TELEMETRY_METRICS_FILE = TELEMETRY_DIR / "metrics.jsonl"

def log_event(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Log a structured event with timestamp and payload.
    
    Args:
        event_type: Type of event (e.g., 'video_start', 'ai_analysis', 'error')
        payload: Additional data about the event
    """
    ts = time.time()
    line = {"timestamp": ts, "event_type": event_type, **payload}
    
    # Write to JSONL file
    with open(TELEMETRY_EVENTS_FILE, "a") as f:
        f.write(json.dumps(line) + "\n")
    
    # Log to standard logging
    logging.info(f"Event: {event_type} - {json.dumps(payload)}")
    
    # Send to webhook if configured
    webhook = os.getenv("TELEMETRY_WEBHOOK_URL")
    if webhook:
        try:
            requests.post(webhook, json={"event": event_type, "data": line}, timeout=5)
        except Exception as e:
            logging.error(f"Failed to send telemetry to webhook: {e}")

def log_metric(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
    """
    Log a performance metric.
    
    Args:
        metric_name: Name of the metric
        value: Numeric value
        tags: Optional tags for categorization
    """
    ts = time.time()
    line = {
        "timestamp": ts,
        "metric": metric_name,
        "value": value,
        "tags": tags or {}
    }
    
    with open(TELEMETRY_METRICS_FILE, "a") as f:
        f.write(json.dumps(line) + "\n")
    
    logging.info(f"Metric: {metric_name}={value} {tags}")

def log_video_processing_start(video_path: str, video_size: int) -> None:
    """Log video processing start event."""
    log_event("video_processing_start", {
        "video_path": video_path,
        "video_size_bytes": video_size
    })

def log_video_processing_end(video_path: str, frames_processed: int, duration: float) -> None:
    """Log video processing completion event."""
    log_event("video_processing_end", {
        "video_path": video_path,
        "frames_processed": frames_processed,
        "duration_seconds": duration
    })

def log_ai_analysis_start(image_path: str, image_size: int) -> None:
    """Log AI analysis start event."""
    log_event("ai_analysis_start", {
        "image_path": image_path,
        "image_size_bytes": image_size
    })

def log_ai_analysis_end(image_path: str, observation: str, processing_time: float) -> None:
    """Log AI analysis completion event."""
    log_event("ai_analysis_end", {
        "image_path": image_path,
        "observation_length": len(observation),
        "processing_time_seconds": processing_time,
        "theft_detected": "Yes" in observation
    })

def log_database_operation(operation: str, table: str, rows_affected: int = 0) -> None:
    """Log database operations."""
    log_event("database_operation", {
        "operation": operation,
        "table": table,
        "rows_affected": rows_affected
    })

def log_error(error_type: str, error_message: str, context: Dict[str, Any]) -> None:
    """Log error events."""
    log_event("error", {
        "error_type": error_type,
        "error_message": str(error_message),
        "context": context
    })

def log_system_info() -> None:
    """Log system information at startup."""
    import platform
    import psutil
    
    log_event("system_info", {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_count": psutil.cpu_count(),
        "memory_total_gb": psutil.virtual_memory().total / (1024**3),
        "disk_free_gb": psutil.disk_usage('/').free / (1024**3)
    })

def get_telemetry_summary() -> Dict[str, Any]:
    """Get summary of telemetry data."""
    try:
        events_count = 0
        if TELEMETRY_EVENTS_FILE.exists():
            with open(TELEMETRY_EVENTS_FILE, "r") as f:
                events_count = sum(1 for _ in f)
        
        metrics_count = 0
        if TELEMETRY_METRICS_FILE.exists():
            with open(TELEMETRY_METRICS_FILE, "r") as f:
                metrics_count = sum(1 for _ in f)
        
        return {
            "events_logged": events_count,
            "metrics_logged": metrics_count,
            "telemetry_dir": str(TELEMETRY_DIR),
            "log_file": str(TELEMETRY_DIR / "app_telemetry.log")
        }
    except Exception as e:
        return {"error": str(e)}
