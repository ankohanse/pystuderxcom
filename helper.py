
import asyncio


class RunHelper():
    """Helper class to run the example code after converting from async to sync"""
    @staticmethod
    def run(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            asyncio.run(func(*args, **kwargs))
        else:
            func(*args, **kwargs)
            