"""
xcom_api_serial.py: communication api to Studer Xcom via serial port.

NOTE: this is a draft implementation that has never been tested against a Xcom-232i.
      Unlike the XcomApiTcp and XcomApiUdp that have indeed been verified against a real Xcom-LAN.
"""

import asyncio
import binascii
import logging
import socket
import serial
import serial_asyncio



from .api_base_async import (
    AsyncXcomApiBase,
    XcomApiReadException,
    XcomApiTimeoutException,
    XcomApiWriteException,
)
from .api_base_sync import (
    XcomApiBase,
)
from .const import (
    START_TIMEOUT,
    REQ_TIMEOUT,
)
from .factory_async import (
    AsyncXcomFactory,
)
from .factory_sync import (
    XcomFactory,
)
from .protocol import (
    XcomPackage,
)


_LOGGER = logging.getLogger(__name__)


DEFAULT_PORT = 'COM3'   # For Windows, or '/dev/ttyUSB0' for Linux
DEFAULT_BAUDRATE = 115200
DEFAULT_DATA_BITS = 8
DEFAULT_STOP_BITS = serial_asyncio.serial.STOPBITS_ONE
DEFAULT_PARITY = serial_asyncio.serial.PARITY_NONE

SERIAL_TERMINATOR = b'\x0D\x0A' # from Studer Xcom documentation


##
## Class implementing Xcom-232i serial protocol
##
class AsyncXcomApiSerial(AsyncXcomApiBase):

    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE):
        """
        Initialize a new XcomApiSerial object.
        """
        super().__init__()

        self.port = port
        self.baudrate = baudrate

        self._reader = None
        self._writer = None
        self._connected = False


    async def start(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the serial connection to the Xcom-232i client.
        """
        if not self._connected:
            _LOGGER.info(f"Xcom-232i serial connection start via {self.port}")

            # Open serial connection.
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url = self.port, 
                baudrate = self.baudrate,
                bytesize = DEFAULT_DATA_BITS,
                stopbits = DEFAULT_STOP_BITS,
                parity = DEFAULT_PARITY
            )
            self._connected = True
        else:
            _LOGGER.info(f"Xcom-232i serial connection already connected to {self.port}")
        
        return True


    async def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        if not self._connected:
            return
        
        _LOGGER.info(f"Stopping Xcom-232i serial connection via {self.port}")
        try:
            self._connected = False

            # Close the writer; we do not need to close the reader
            if self._writer and not self._writer.is_closing:
                self._writer.close()
                await self._writer.wait_closed()
                await asyncio.sleep(0.5) # Wait for half a second for the OS to release the port

        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom writer: {e}")

        self._reader = None
        self._writer = None
        _LOGGER.info(f"Stopped Xcom-232i serial Connection")
    

    async def _sendPackage(self, package: XcomPackage):
        """
        Send an Xcom package.
        Exception handling is dealed with by the caller
        """
        data = package.getBytes()

        self._writer.write(data)
        await self._writer.drain()
    

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
## Class implementing Xcom-232i serial protocol
##
class XcomApiSerial(XcomApiBase):

    def __init__(self, port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE):
        """
        Initialize a new XcomApiSerial object.
        """
        super().__init__()

        self.port: int = port
        self.baudrate: int = baudrate

        self._serial: serial.Serial = None
        self._connected: bool = False


    def start(self, timeout=START_TIMEOUT) -> bool:
        """
        Start the serial connection to the Xcom-232i client.
        """
        if not self._connected:
            _LOGGER.info(f"Xcom-232i serial connection start via {self.port}")

            # Open serial connection.
            self._serial = serial.Serial(
                port = self.port, 
                baudrate = self.baudrate,
                bytesize = DEFAULT_DATA_BITS,
                stopbits = DEFAULT_STOP_BITS,
                parity = DEFAULT_PARITY,
                timeout = REQ_TIMEOUT
            )
            self._connected = True
        else:
            _LOGGER.info(f"Xcom-232i serial connection already connected to {self.port}")
        
        return True


    def stop(self):
        """
        Stop listening to the the Xcom Client and stop the Xcom Server.
        """
        if not self._connected:
            return
        
        _LOGGER.info(f"Stopping Xcom-232i serial connection")
        try:
            self._connected = False

            # Close the writer; we do not need to close the reader
            if self._serial and self._serial.is_open:
                self._serial.close()
    
        except Exception as e:
            _LOGGER.warning(f"Exception during closing of Xcom writer: {e}")

        self._serial = None
        _LOGGER.info(f"Stopped Xcom-232i serial Connection")
    

    def _sendPackage(self, package: XcomPackage):
        """
        Send an Xcom package.
        Exception handling is dealed with by the caller
        """
        data = package.getBytes()

        self._serial.write(data)
    

    def _receivePackage(self) -> XcomPackage | None:
        """
        Attempt to receive an Xcom package. 
        Return None of nothing was received within REQ_TIMEOUT
        Exception handling is dealed with by the caller
        """
        try:
            return XcomFactory.parse_package(self._serial, REQ_TIMEOUT)

        except socket.timeout:
            return None

 