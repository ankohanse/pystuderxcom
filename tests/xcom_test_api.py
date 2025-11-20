
import logging

from pystuderxcom import (
    AsyncXcomApiBase,
    XcomApiBase,
    XcomPackage,
)


_LOGGER = logging.getLogger(__name__)


class AsyncTestApi(AsyncXcomApiBase):
    """
    Derived class to help test the parent class
    """
    def __init__(self, on_send_handler=None, on_receive_handler=None, rsp_dest=None, rsp_dict=None):
        super().__init__()
        self._on_send = on_send_handler
        self._on_receive = on_receive_handler
        self.rsp_dest = rsp_dest
        self.rsp_dict = rsp_dict

        # Simulate we already have started"""
        self._connected = True  
        self._remote_ip = "127.0.0.1"  
    
        # Internal variables to keep track of what happened during the test
        self.send_called: bool = False
        self.receive_called: bool = False
        self.request_package: XcomPackage = None
        self.response_package: XcomPackage = None

    async def _send_package(self, package: XcomPackage):
        self.send_called = True
        self.request_package = package

        if self._on_send:
            await self._on_send(self)

    async def _receive_package(self) -> XcomPackage | None:
        if self._on_receive:
            await self._on_receive(self)

        self.receive_called = True
        return self.response_package
    


class TestApi(XcomApiBase):
    """
    Derived class to help test the parent class
    """
    def __init__(self, on_send_handler=None, on_receive_handler=None, rsp_dest=None, rsp_dict=None):
        super().__init__()
        self._on_send = on_send_handler
        self._on_receive = on_receive_handler
        self.rsp_dest = rsp_dest
        self.rsp_dict = rsp_dict

        # Simulate we already have started"""
        self._connected = True  
        self._remote_ip = "127.0.0.1"  
    
        # Internal variables to keep track of what happened during the test
        self.send_called: bool = False
        self.receive_called: bool = False
        self.request_package: XcomPackage = None
        self.response_package: XcomPackage = None

    def _send_package(self, package: XcomPackage):
        self.send_called = True
        self.request_package = package

        if self._on_send:
            self._on_send(self)

    def _receive_package(self) -> XcomPackage | None:
        if self._on_receive:
            self._on_receive(self)

        self.receive_called = True
        return self.response_package
    
