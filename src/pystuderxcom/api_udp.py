"""xcom_api.py: communication api to Studer Xcom via LAN."""

import asyncio
import asyncudp
import binascii
import logging
import socket

from datetime import datetime, timedelta
from typing import Iterable

from pystuderxcom.protocol import XcomPackage


from .api_base_async import (
    AsyncXcomApiBase,
    XcomApiWriteException,
    XcomApiReadException,
    XcomApiTimeoutException,
    XcomApiUnpackException,
    XcomApiResponseIsError,
)
from .api_base_sync import (
    XcomApiBase,
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
from .values import (
    XcomValues,
    XcomValuesItem,
)


_LOGGER = logging.getLogger(__name__)


DEFAULT_LOCAL_PORT = 4001
DEFAULT_REMOTE_PORT = 4001


##
## Class implementing Xcom-LAN UDP network protocol
##
class AsyncXcomApiUdp(AsyncXcomApiBase):

    def __init__(self, remote_ip: str, remote_port=DEFAULT_REMOTE_PORT, local_port=DEFAULT_LOCAL_PORT):
        """
        We connect to the Moxa using the Udp server we are creating here.
        Once it is started we can send package requests. 
        """
        super().__init__()

        self._remote_ip: str = remote_ip
        self._remote_port: int = remote_port
        self._local_port: int = local_port

        self._socket: asyncudp.Socket = None
        self._connected: bool = False


    async def start(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the Xcom Server and listening to the Xcom client.
        """
        if not self._connected:
            _LOGGER.info(f"Xcom UDP server start listening on port {self._local_port}")

            self._socket = await asyncudp.create_socket(local_addr=('0.0.0.0', self._local_port), packets_queue_max_size=100)
            self._connected = True
        else:
            _LOGGER.info(f"Xcom UDP server already listening on port {self._local_port}")

        return True


    async def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        _LOGGER.info(f"Stopping Xcom UDP server")
        try:
            self._connected = False

            # Close the writer; we do not need to close the reader
            if self._socket:
                self._socket.close()
                self._socket = None
                
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom socket: {e}")

        self._connected = False
        _LOGGER.info(f"Stopped Xcom UDP server")


    async def _sendPackage(self, package: XcomPackage):
        """
        Send an Xcom package.
        Exception handling is dealed with by the caller
        """
        data = package.getBytes()
        addr = (self._remote_ip, self._remote_port)

        self._socket.sendto(data, addr=addr )
    

    async def _receivePackage(self) -> XcomPackage | None:
        """
        Attempt to receive an Xcom package. 
        Return None of nothing was received within REQ_TIMEOUT
        Exception handling is dealed with by the caller
        """
        try:
            async with asyncio.timeout(REQ_TIMEOUT):
                data,_ = await self._socket.recvfrom()
            
                return await AsyncXcomFactory.parse_package_bytes(data)
        
        except asyncio.exceptions.TimeoutError:
            return None
        except asyncio.exceptions.CancelledError:
            return None



##
## Class implementing Xcom-LAN UDP network protocol
##
class XcomApiUdp(XcomApiBase):

    def __init__(self, remote_ip: str, remote_port=DEFAULT_REMOTE_PORT, local_port=DEFAULT_LOCAL_PORT):
        """
        We connect to the Moxa using the Udp server we are creating here.
        Once it is started we can send package requests. 
        """
        super().__init__()

        self._remote_ip: str = remote_ip
        self._remote_port: int = remote_port
        self._local_port: int = local_port
        self._socket: socket.Socket = None
        self._connected: bool = False


    def start(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the Xcom Server and listening to the Xcom client.
        """
        if not self._connected:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.bind(("", self._local_port))
            self._socket.settimeout(2) # as recommended by Studer Xcom documentation

            self._connected = True
        else:
            _LOGGER.info(f"Xcom UDP server already listening on port {self._local_port}")

        return True


    def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        _LOGGER.info(f"Stopping Xcom UDP server")
        try:
            if self._socket:
                self._socket.close()
                self._socket = None
        
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom socket: {e}")

        self._connected = False
        _LOGGER.info(f"Stopped Xcom UDP server")


    def _sendPackage(self, package: XcomPackage):
        """
        Send an Xcom package.
        Exception handling is dealed with by the caller
        """
        data = package.getBytes()
        addr = (self._remote_ip, self._remote_port)

        self._socket.sendto(data, addr)
    

    def _receivePackage(self) -> XcomPackage | None:
        """
        Attempt to receive an Xcom package. 
        Return None of nothing was received within REQ_TIMEOUT
        Exception handling is dealed with by the caller
        """
        try:
            data = self._socket.recv(XcomPackage.max_length)
            
            return XcomFactory.parse_package_bytes(data)

        except socket.timeout:
            return None

