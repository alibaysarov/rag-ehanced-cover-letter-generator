from functools import wraps

from app.dependencies import get_pub_sub_listener

listener = get_pub_sub_listener()


def response_listener(redis_chan: str):
    def decorator(func):
        listener.attach_listener(redis_chan, func)

        @wraps(func)
        async def wrapper(data: dict):
            return await func(data)

        return wrapper

    return decorator
