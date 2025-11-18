"""xcom_api.py: communication api to Studer Xcom via LAN."""

import asyncio
import logging
import socket

from pystuderxcom import  (
    AsyncXcomApiTcp, XcomApiTcp,
    AsyncXcomFactory, XcomFactory,
    XcomApiTimeoutException,
    XcomApiReadException,
    XcomApiWriteException,
    XcomPackage,
)

_LOGGER = logging.getLogger(__name__)


DEFAULT_PORT = 54001
START_TIMEOUT = 30 # seconds
STOP_TIMEOUT = 5
REQ_TIMEOUT = 2
REQ_RETRIES = 3


##
## Class implementing Xcom-LAN TCP network protocol
##
class AsyncTestClientTcp():

    def __init__(self, port=DEFAULT_PORT):
        """
        MOXA is connecting to the TCP Server we are creating here.
        Once it is connected we can send package requests.
        """
        super().__init__()

        self.port = port
        self._reader = None
        self._writer = None
        self._started = False
        self._connected = False
        self._remote_ip = None

        self._receivePackageLock = asyncio.Lock() # to make sure receivePackage is never called concurrently
        self._sendPackageLock    = asyncio.Lock() # to make sure sendPackage is never called concurrently


    @property
    def connected(self):
        """Returns True if the Xcom client is connected, otherwise False"""
        return self._connected


    @property
    def remote_ip(self) -> str|None:
        """Returns the IP address of the connected Xcom client, otherwise None"""
        return self._remote_ip


    async def start(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the Xcom Client and listening to the Xcom server.
        """
        if not self._started:
            _LOGGER.info(f"Xcom TCP Test Client connect to port {self.port}")

            self._reader, self._writer = await asyncio.open_connection("127.0.0.1", self.port, limit=1000, family=socket.AF_INET)

            (self._remote_ip,_) = self._writer.get_extra_info("peername")
            _LOGGER.info(f"Connected to Xcom server '{self._remote_ip}'")

            self._started = True
            self._connected = True
        else:
            _LOGGER.info(f"Xcom TCP Test Client already listening on port {self.port}")


    async def stop(self):
        """
        Stop listening to the the Xcom Server and stop the Xcom TCP Test Client
        """
        _LOGGER.info(f"Stopping Xcom TCP Test Client")
        try:
            self._connected = False

            # Close the writer; we do not need to close the reader
            if self._writer:
                self._writer.close()
                await self._writer.wait_closed()
    
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom writer: {e}")

        self._started = False
        _LOGGER.info(f"Stopped Xcom TCP Test Client")
    

    async def receivePackage(self, timeout=REQ_TIMEOUT) -> XcomPackage | None:
        """
        Receive an Xcom package from Server to Client
        Throws:
            XcomApiWriteException
            XcomApiReadException
            XcomApiTimeoutException
        """
        if not self._connected:
            _LOGGER.info(f"receivePackage - not connected")
            return None
        
        async with self._receivePackageLock:
            # Receive a package
            try:
                async with asyncio.timeout(timeout):
                    while True:
                        request = await AsyncXcomFactory.parse_package(self._reader)
                        if request is not None:
                            _LOGGER.info(f"Xcom TCP Test Client received request package {request}")
                            return request

            except asyncio.TimeoutError as te:
                msg = f"Timeout while listening for request package from Xcom server"
                raise XcomApiTimeoutException(msg) from None

            except Exception as e:
                msg = f"Exception while listening for request package from Xcom server: {e}"
                raise XcomApiReadException(msg) from None


    async def sendPackage(self, package: XcomPackage, timeout=REQ_TIMEOUT):
        """
        Send an Xcom package from Client to Server
        Throws:
            XcomApiWriteException
            XcomApiReadException
            XcomApiTimeoutException
        """
        if not self._connected:
            _LOGGER.info(f"sendPackage - not connected")
            return None
        
        async with self._sendPackageLock:
            # Send the package to the Xcom server
            try:
                _LOGGER.info(f"Xcom TCP Test Client send response package {package}")
                self._writer.write(package.getBytes())
                await self._writer.drain()

            except Exception as e:
                msg = f"Exception while sending package to Xcom server: {e}"
                raise XcomApiWriteException(msg) from None



##
## Class implementing Xcom-LAN TCP network protocol
##
class TestClientTcp(XcomApiTcp):

    # We mostly have the same behavior as the TCP Server
    # Except ofcourse that we start as TCP Client, not Server...
    def start(self, timeout=START_TIMEOUT, wait_for_connect=True) -> bool:
        """
        Start the Xcom Client and connect to the Xcom Server
        """
        if not self._started:
            _LOGGER.info(f"Xcom TCP Client connect to port {self.port}")

            self._connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._connection.connect(("localhost", self.port))
            self._started = True
            self._connected = True
        else:
            _LOGGER.info(f"Xcom TCP Client already connected to port {self.port}")
        
        return True    


    def stop(self):
        """
        Stop connection to the the Xcom Server
        """
        _LOGGER.info(f"Stopping Xcom TCP Client")
        try:
            self._connected = False

            if self._connection is not None:
                self._connection.close()
                self._connection = None
    
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom Client connection: {e}")

        self._started = False
        _LOGGER.info(f"Stopped Xcom TCP Test Client")
    

    def receivePackage(self) -> XcomPackage | None:
        return super()._receivePackage()


    def sendPackage(self, package: XcomPackage):
        return super()._sendPackage(package)
