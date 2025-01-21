import logging
import os
from datetime import datetime
from functools import wraps
import traceback
import time

class AutocompleteLogger:
    def __init__(self):
        # Create logs directory if it doesn't exist
        self.log_dir = os.path.expanduser("~/.textual_editor/logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"autocomplete_{timestamp}.log")
        
        # Configure logging
        self.logger = logging.getLogger("autocomplete")
        self.logger.setLevel(logging.DEBUG)
        
        # File handler with detailed formatting
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Performance tracking
        self.perf_data = {}
    
    def log_completion_request(self, word: str, context: str):
        """Log when completion is requested"""
        self.logger.debug(f"Completion requested for word: '{word}' with context: '{context}'")
    
    def log_completion_results(self, completions: list, duration: float):
        """Log completion results and timing"""
        self.logger.debug(
            f"Found {len(completions)} completions in {duration:.3f}s: "
            f"{[c.name for c in completions[:5]]}{'...' if len(completions) > 5 else ''}"
        )
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = None):
        """Log cache operations"""
        if hit is not None:
            self.logger.debug(f"Cache {operation} for '{key}': {'HIT' if hit else 'MISS'}")
        else:
            self.logger.debug(f"Cache {operation} for '{key}'")
    
    def log_error(self, error: Exception, context: str):
        """Log errors with stack trace"""
        self.logger.error(
            f"Error in {context}: {str(error)}\n"
            f"Stack trace: {traceback.format_exc()}"
        )
    
    def log_score(self, suggestion_name: str, score: float, factors: dict):
        """Log scoring details"""
        self.logger.debug(
            f"Scoring '{suggestion_name}': {score:.2f} - Factors: {factors}"
        )
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.perf_data[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and log duration"""
        if operation in self.perf_data:
            duration = time.time() - self.perf_data[operation]
            self.logger.debug(f"{operation} took {duration:.3f}s")
            del self.perf_data[operation]
            return duration
        return 0.0

def log_method(logger_attr='_logger'):
    """Decorator to log method calls and timing"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            logger = getattr(self, logger_attr)
            method_name = func.__name__
            
            logger.logger.debug(f"Entering {method_name}")
            logger.start_timer(method_name)
            
            try:
                result = func(self, *args, **kwargs)
                logger.end_timer(method_name)
                return result
            except Exception as e:
                logger.log_error(e, method_name)
                raise
            
        return wrapper
    return decorator