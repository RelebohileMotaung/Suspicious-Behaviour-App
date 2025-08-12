"""
Google API Configuration for handling GOOGLE_API_KEY and rate limiting
"""

import os
import logging
from functools import wraps
import time
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class GoogleAPIConfig:
    """Configuration for Google API with graceful handling of missing keys and rate limiting"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.is_enabled = bool(self.api_key)
        self.rate_limit_delay = float(os.getenv("GOOGLE_API_RATE_LIMIT_DELAY", "1.0"))
        self.max_retries = int(os.getenv("GOOGLE_API_MAX_RETRIES", "3"))
        
    def get_api_key(self) -> Optional[str]:
        """Get Google API key from environment"""
        return self.api_key
    
    def is_api_enabled(self) -> bool:
        """Check if Google API is enabled"""
        return self.is_enabled
    
    def log_api_status(self):
        """Log current API status"""
        if self.is_enabled:
            logger.info("Google API is enabled")
        else:
            logger.warning("GOOGLE_API_KEY not found - AI features will be disabled")
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            "delay": self.rate_limit_delay,
            "max_retries": self.max_retries
        }

def rate_limit(func):
    """Decorator to add rate limiting to API calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        config = GoogleAPIConfig()
        if not config.is_api_enabled():
            return None
            
        for attempt in range(config.max_retries):
            try:
                # Add exponential backoff
                if attempt > 0:
                    delay = config.rate_limit_delay * (2 ** attempt)
                    time.sleep(delay)
                return func(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) and attempt < config.max_retries - 1:
                    logger.warning(f"Rate limit hit, retrying in {config.rate_limit_delay * (2 ** attempt)}s")
                    continue
                else:
                    logger.error(f"API call failed: {e}")
                    return None
        return None
    return wrapper

def get_safe_eval_result():
    """Get safe evaluation result when API is disabled"""
    return "DISABLED"

def get_safe_analysis_result():
    """Get safe analysis result when API is disabled"""
    return "AI analysis disabled - no API key", {}
