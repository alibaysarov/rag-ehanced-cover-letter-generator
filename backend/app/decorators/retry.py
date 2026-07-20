import functools
import logging
import random
import time

logger = logging.getLogger(__name__)

def retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,)):
    """
    A retry decorator with exponential backoff and random jitter.
    """
    def decorator(func):
        @functools.wraps(func)  # Preserves the original function's metadata
        def wrapper(*args, **kwargs):
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        print(f"❌ Attempt {attempt} failed. Out of retries.")
                        raise e  # Re-raise the exception after last failure
                    
                    # Calculate next delay with exponential backoff + jitter
                    jitter = random.uniform(0, 0.5) * current_delay
                    sleep_time = current_delay + jitter
                    
                    logger.info(f"⚠️ Attempt {attempt} failed: {e}. Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    current_delay *= backoff
                    
        return wrapper
    return decorator