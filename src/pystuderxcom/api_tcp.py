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
    XcomApiTcpMode,
    XcomLevel,
    XcomFormat,
    XcomCategory,
    XcomAggregationType,
    ScomAddress,
    ScomObjType,
    ScomObjId,
    ScomService,
    ScomQspId,
    ScomErrorCode,
    XcomParamException,
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

    def __init__(self, mode:XcomApiTcpMode=XcomApiTcpMode.SERVER, listen_port=DEFAULT_PORT, remote_ip:str=None, remote_port:int=None):
        """
        Usage: AsyncXcomApiTcp(mode=XcomApiTcpMode.SERVER, listen_port=port)
        or:    AsyncXcomApiTcp(mode=XcomApiTcpMode.CLIENT, remote_ip=ip, remote_port=port)
        
        In Server mode, MOXA needs to be running as TCP Client and will be connecting to the TCP Server we are creating here.
        In Client mode, MOXA needs to be running as TCP Server and will listen for a connection from the TCP client we are creating here.

        In both cases, once connected we can send package requests.
        """
        super().__init__()

        # Sanity check
        match mode:
            case XcomApiTcpMode.CLIENT:
                if remote_ip is None: raise XcomParamException("Parameter 'remote_ip' was not specified")
                if remote_port is None: raise XcomParamException("Parameter 'remote_port' was not specified")
            case XcomApiTcpMode.SERVER:
                if listen_port is None: raise XcomParamException("Parameter 'listen_port' was not specified")
            case _:
                raise XcomParamException(f"Parameter 'mode' has an incorrect value '{mode}'")

        # Remember our parameters
        self._mode: XcomApiTcpMode = mode
        self._listen_port: int = listen_port    # Only applicable if mode=SERVER
        self._remote_ip = remote_ip      # Only applicable if mode=CLIENT
        self._remote_port = remote_port  # Only applicable if mode=CLIENT

        # Internal administration
        self._server: asyncio.Server = None
        self._connection: socket.socket = None
        self._reader: asyncio.StreamReader = None
        self._writer: asyncio.StreamWriter = None
        self._started: bool = False
        self._connected: bool = False


    async def start(self, timeout=START_TIMEOUT, wait_for_connect=True) -> bool:
        """
        Start the Xcom Server or Client
        """
        match self._mode:
            case XcomApiTcpMode.CLIENT: return await self._start_client(timeout)
            case XcomApiTcpMode.SERVER: return await self._start_server(timeout, wait_for_connect)

    
    async def _start_client(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the Xcom client and connect to the Xcom server
        """        
        if not self._started:
            _LOGGER.info(f"Xcom TCP client connect to {self._remote_ip}:{self._remote_port}")

            self._reader, self._writer = await asyncio.open_connection(self._remote_ip, self._remote_port, limit=1000, family=socket.AF_INET)

            _LOGGER.info(f"Connected to Xcom server '{self._remote_ip}'")
            self._started = True
            self._connected = True
        else:
            _LOGGER.info(f"Xcom TCP client already connected to {self._remote_ip}:{self._remote_port}")
        
        return True


    async def _start_server(self, timeout=START_TIMEOUT, wait_for_connect=True) -> bool:
        """
        Start the Xcom Server and listening to the Xcom client.
        """        
        if not self._started:
            _LOGGER.info(f"Xcom TCP server start listening on port {self._listen_port}")

            self._server = await asyncio.start_server(self._client_connected_callback, "0.0.0.0", self._listen_port, limit=1000, family=socket.AF_INET)
            self._server._start_serving()
            self._started = True
        else:
            _LOGGER.info(f"Xcom TCP server already listening on port {self.listen_port}")

        if wait_for_connect:
            _LOGGER.info("Waiting for Xcom TCP client to connect...")
            return await self._wait_until_connected(timeout)
        
        return True


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


    async def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        match self._mode:
            case XcomApiTcpMode.SERVER: name = "Xcom TCP server"
            case XcomApiTcpMode.CLIENT: name = "Xcom TCP client"

        _LOGGER.info(f"Stopping {name}")
        try:
            self._connected = False

            # Close the writer; we do not need to close the reader
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
    
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom writer: {e}")

        # Close the server (if any)
        try:
            if self._server:
                async with asyncio.timeout(STOP_TIMEOUT):
                    self._server.close()
                    await self._server.wait_closed()
    
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom server: {e}")

        self._started = False
        _LOGGER.info(f"Stopped {name}")
    

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

    def __init__(self, mode:XcomApiTcpMode=XcomApiTcpMode.SERVER, listen_port=DEFAULT_PORT, remote_ip:str=None, remote_port:int=None):
        """
        Usage: XcomApiTcp(mode=XcomApiTcpMode.SERVER, listen_port=port)
        or:    XcomApiTcp(mode=XcomApiTcpMode.CLIENT, remote_ip=ip, remote_port=port)
        
        In Server mode, MOXA needs to be running as TCP Client and will be connecting to the TCP Server we are creating here.
        In Client mode, MOXA needs to be running as TCP Server and will listen for a connection from the TCP client we are creating here.

        In both cases, once connected we can send package requests.
        """
        super().__init__()

        # Sanity check
        match mode:
            case XcomApiTcpMode.CLIENT:
                if remote_ip is None: raise XcomParamException("Paramater 'remote_ip' was not specified")
                if remote_port is None: raise XcomParamException("Paramater 'remote_port' was not specified")
            case XcomApiTcpMode.SERVER:
                if listen_port is None: raise XcomParamException("Paramater 'listen_port' was not specified")

        # Remember our parameters
        self._mode: XcomApiTcpMode = mode
        self._listen_port: int = listen_port    # Only applicable if mode=SERVER
        self._remote_ip = remote_ip      # Only applicable if mode=CLIENT
        self._remote_port = remote_port  # Only applicable if mode=CLIENT

        # internal administration
        self._server: socket.socket = None
        self._connection: socket.socket = None
        self._started: bool = False
        self._connected: bool = False


    def start(self, timeout=START_TIMEOUT, wait_for_connect:bool = False) -> bool:
        """
        Start the Xcom Server or Client
        """
        match self._mode:
            case XcomApiTcpMode.CLIENT: return self._start_client(timeout)
            case XcomApiTcpMode.SERVER: return self._start_server(timeout)

    
    def _start_client(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the Xcom client and connect to the Xcom server
        """        
        if not self._started:
            _LOGGER.info(f"Xcom TCP Client connect to {self._remote_ip}:{self._remote_port}")

            self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._connection.connect((self._remote_ip, self._remote_port))
            self._connection.settimeout(REQ_TIMEOUT)
            self._started = True
            self._connected = True
        else:
            _LOGGER.info(f"Xcom TCP Client already connected to {self._remote_ip}:{self._remote_port}")
        
        return True    


    def _start_server(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the Xcom Server and listening to the Xcom client.
        """
        if not self._started:
            _LOGGER.info(f"Xcom TCP server start listening on port {self._listen_port}")

            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind(("0.0.0.0", self._listen_port))
            self._server.listen(1)
            self._server.settimeout(timeout)
            self._started = True

            self._connection, addr = self._server.accept()
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
        match self._mode:
            case XcomApiTcpMode.SERVER: name = "Xcom TCP server"
            case XcomApiTcpMode.CLIENT: name = "Xcom TCP client"

        _LOGGER.info(f"Stopping {name}")
        try:
            self._connected = False

            if self._connection is not None:
                self._connection.close()
                self._connection = None

        except Exception as e:
           _LOGGER.warning(f"Exception during closing of tcp connection: {e}")

        try:
            if self._server is not None:
                self._server.close()
                self._server = None

        except Exception as e:
           _LOGGER.warning(f"Exception during closing of tcp server: {e}")
        
        self._started = False
        _LOGGER.info(f"Stopped {name}")
        

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
