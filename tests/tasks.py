

import asyncio
import threading


class AsyncTaskHelper:
    """
    Helper to unify async task create, sleep and stop
    """
    def __init__(self, target_function, *args, **kwargs):
        self.target_function = target_function
        self.args = args
        self.kwargs = kwargs
        self.result = None

        self._task = None

    async def start(self):
        coro = self.target_function(*self.args, **self.kwargs)
        self._task = asyncio.create_task(coro=coro, name=self.target_function.__name__)
        return self
    
    async def join(self):
        # await the task to allow it to finish and cleanup
        self.result = await self._task
        return self.result

         
class TaskHelper(threading.Thread):
    """
    Helper to unify sync task create, sleep and stop
    """
    def __init__(self, target_function, *args, **kwargs):
        super().__init__()
        self.target_function = target_function
        self.args = args
        self.kwargs = kwargs
        self.name = target_function.__name__
        self.result = None

    def start(self):
        super().start()
        return self
    
    def run(self):
        """Called internally after start()"""
        self.result = self.target_function(*self.args, **self.kwargs)

    def join(self):
        super().join()
        return self.result
         
    