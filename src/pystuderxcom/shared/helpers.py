import asyncio
import threading
from types import TracebackType
from typing import Optional, Type

class HybridLock:
    """A lock that can be used interchangeably with both 'with' and 'async with'."""
    
    def __init__(self) -> None:
        self._lock = threading.Lock()

    # --- Synchronous Context Manager Protocol ---
    def __enter__(self) -> "HybridLock":
        self._lock.acquire()
        return self

    def __exit__(
        self, 
        exc_type: Optional[Type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional[TracebackType]
    ) -> None:
        self._lock.release()

    # --- Asynchronous Context Manager Protocol ---
    async def __aenter__(self) -> "HybridLock":
        # Run the blocking acquire() inside an executor thread 
        # so it doesn't stall the async event loop.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._lock.acquire)
        return self

    async def __aexit__(
        self, 
        exc_type: Optional[Type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional[TracebackType]
    ) -> None:
        # Releasing a threading.Lock is instantaneous and non-blocking
        self._lock.release()
