"""xcom_api.py: communication api to Studer Xcom via LAN."""

import asyncio
import binascii
import logging
import socket

from datetime import datetime, timedelta
import threading
from typing import Iterable


from .api_base_async import (
    AsyncXcomApiBase,
    XcomApiWriteException,
    XcomApiReadException,
    XcomApiTimeoutException,
    XcomApiUnpackException,
    XcomApiResponseIsError,
)
from .api_base_sync import (
    XcomApiBase
)
from .const import (
    START_TIMEOUT,
    STOP_TIMEOUT,
    REQ_TIMEOUT,
    ScomAddress,
    XcomLevel,
    XcomFormat,
    XcomCategory,
    XcomAggregationType,
    ScomObjType,
    ScomObjId,
    ScomService,
    ScomQspId,
    ScomErrorCode,
    XcomParamException,
    safe_len,
)
from .data import (
    XcomData,
    XcomDataMessageRsp,
    MULTI_INFO_REQ_MAX,
)
from .factory_async import (
    AsyncXcomFactory,
)
from .factory_sync import (
    XcomFactory,
)
from .families import (
    XcomDeviceFamilies
)
from .messages import (
    XcomMessage,
)
from .protocol import (
    XcomPackage,
)
from .values import (
    XcomValues,
    XcomValuesItem,
)


_LOGGER = logging.getLogger(__name__)


DEFAULT_PORT = 4001


##
## Class implementing Xcom-LAN TCP network protocol
##
class AsyncXcomApiTcp(AsyncXcomApiBase):

    def __init__(self, port=DEFAULT_PORT):
        """
        MOXA is connecting to the TCP Server we are creating here.
        Once it is connected we can send package requests.
        """
        super().__init__()

        self.port: int = port
        self._server: asyncio.Server = None
        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamWriter = None
        self._started: bool = False
        self._connected: bool = False
        self._remote_ip: str = None


    async def start(self, timeout=START_TIMEOUT, wait_for_connect=True) -> bool:
        """
        Start the Xcom Server and listening to the Xcom client.
        """
        if not self._started:
            _LOGGER.info(f"Xcom TCP server start listening on port {self.port}")

            self._server = await asyncio.start_server(self._client_connected_callback, "0.0.0.0", self.port, limit=1000, family=socket.AF_INET)
            self._server._start_serving()
            self._started = True
        else:
            _LOGGER.info(f"Xcom TCP server already listening on port {self.port}")

        if wait_for_connect:
            _LOGGER.info("Waiting for Xcom TCP client to connect...")
            return await self._wait_until_connected(timeout)
        
        return True


    async def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        _LOGGER.info(f"Stopping Xcom TCP server")
        try:
            self._connected = False

            # Close the writer; we do not need to close the reader
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
    
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom writer: {e}")

        # Close the server
        try:
            async with asyncio.timeout(STOP_TIMEOUT):
                if self._server:
                    self._server.close()
                    await self._server.wait_closed()
    
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom server: {e}")

        self._started = False
        _LOGGER.info(f"Stopped Xcom TCP server")
    

    async def _client_connected_callback(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Callback called once the Xcom Client connects to our Server
        """
        self._reader = reader
        self._writer = writer
        self._connected = True

        # Gather some info about remote server
        (self._remote_ip,_) = self._writer.get_extra_info("peername")

        _LOGGER.info(f"Connected to Xcom client '{self._remote_ip}'")


    async def _sendPackage(self, package: XcomPackage):
        """
        Send an Xcom package.
        Exception handling is dealed with by the caller
        """
        self._writer.write(package.getBytes())
    

    async def _receivePackage(self) -> XcomPackage | None:
        """
        Attempt to receive an Xcom package. 
        Return None of nothing was received within REQ_TIMEOUT
        Exception handling is dealed with by the caller
        """
        try:
            async with asyncio.timeout(REQ_TIMEOUT):
                return await AsyncXcomFactory.parse_package(self._reader)
        
        except asyncio.exceptions.TimeoutError:
            return None
        except asyncio.exceptions.CancelledError:
            return None
            


##
## Class implementing Xcom-LAN TCP network protocol
##
class XcomApiTcp(XcomApiBase):

    def __init__(self, port=DEFAULT_PORT):
        """
        MOXA is connecting to the TCP Server we are creating here.
        Once it is connected we can send package requests.
        """
        super().__init__()

        self.port: int = port
        self._socket: socket.socket = None
        self._connection: socket.socket = None
        self._started: bool = False
        self._connected: bool = False
        self._remote_ip: str = None


    def start(self, timeout=START_TIMEOUT, wait_for_connect=True) -> bool:
        """
        Start the Xcom Server and listening to the Xcom client.
        """
        if not self._started:
            _LOGGER.info(f"Xcom TCP server start listening on port {self.port}")

            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(("0.0.0.0", self.port))
            self._socket.listen(1)
            self._socket.settimeout(timeout)
            self._started = True

            self._connection, addr = self._socket.accept()
            self._connection.settimeout(REQ_TIMEOUT)
            self._connected = True

            self._remote_ip = addr[0]
        else:
            _LOGGER.info(f"Xcom TCP server already listening on port {self.port}")
        
        return True


    def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        _LOGGER.info(f"Stopping Xcom TCP server")
        try:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

        except Exception as e:
           _LOGGER.warning(f"Exception during closing of tcp connection: {e}")

        try:
            if self._socket is not None:
                self._socket.close()
                self._socket = None

        except Exception as e:
           _LOGGER.warning(f"Exception during closing of tcp server: {e}")

        self._connected = False
        self._started = False
        _LOGGER.info(f"Stopped Xcom TCP server")
        

    def _sendPackage(self, package: XcomPackage):
        """
        Send an Xcom package.
        Exception handling is dealed with by the caller
        """
        self._connection.send(package.getBytes())
    

    def _receivePackage(self) -> XcomPackage | None:
        """
        Attempt to receive an Xcom package. 
        Return None of nothing was received within REQ_TIMEOUT
        Exception handling is dealed with by the caller
        """
        data = self._connection.recv(XcomPackage.max_length)
        
        return XcomFactory.parse_package_bytes(data)
