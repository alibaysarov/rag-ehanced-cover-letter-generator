from contextlib import asynccontextmanager
from functools import wraps
import time
import asyncio


@asynccontextmanager
async def with_timer(label=""):
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000
    print(f"[{label}] выполнено за {elapsed:.3f} мс")


    

def time_performance(func):
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[{func.__name__}] выполнено за {elapsed:.3f} с")
        return result

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[{func.__name__}] выполнено за {elapsed:.3f} с")
        return result

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper