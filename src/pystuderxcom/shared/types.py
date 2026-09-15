"""
Shared Data Types 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

from dataclasses import dataclass
import logging
from enum import IntEnum, StrEnum


_LOGGER = logging.getLogger(__name__)


class StuderDiscoverNotConnected(Exception):
    """Exception to indicate that remote gateway is not connected"""


class StuderUserLevel(IntEnum):
    INFO      = 0x0001
    VIEWONLY  = 0x0000 # View Only
    BASIC     = 0x0010
    EXPERT    = 0x0020
    INSTALLER = 0x0030 # Installer
    STUDER    = 0x0040 # Studer / Qualified Service Person

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name


class StuderAccess(StrEnum):
    READ       = "R"
    WRITE      = "W"
    READ_WRITE = "R/W"

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name


class StuderTarget(StrEnum):
    STANDARD    = "standard"
    VIRTUAL     = "virtual"

    def __str__(self):
            return self.name
        
    def __repr__(self):
        return self.name


class StuderDataType(StrEnum):
    BOOL       = "BOOL"         # 1 byte
    SIGNAL     = "SIGNAL"       # 1 byte
    INT16      = "INT16"        # 2 bytes
    UINT16     = "UINT16"       # 2 bytes
    ENUM16     = "ENUM16"       # 2 bytes
    FORMAT     = "FORMAT"       # 2 bytes
    ERROR      = "ERROR"        # 2 bytes
    INT32      = "INT32"        # 4 bytes
    UINT32     = "UINT32"       # 4 bytes
    FLOAT32    = "FLOAT32"      # 4 bytes
    ENUM32     = "ENUM32"       # 4 bytes
    BITFIELD   = "BITFIELD"     # 4 bytes
    INT64      = "INT64"        # 8 bytes
    UINT64     = "UINT64"       # 8 bytes
    FLOAT64    = "FLOAT64"      # 8 bytes
    GUID       = "GUID"         # 16 bytes
    STRING     = "STRING"       # n bytes
    MENU       = "MENU"         # n.a.
    INVALID    = "INVALID"      # n.a.

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name


@dataclass
class StuderDiscoveredGateway:
    host: str = None
    port: int = None
    guid: str = None


@dataclass
class StuderDiscoveredDevice:
    # Base info
    code: str
    address_or_slave: int  # Xcom uses address, Next uses slave
    family_id: str
    family_model: str

    # Extended info
    device_model: str = None
    serial: str = None
    hw_version: str = None
    sw_version: str = None
    om_version: str = None

    @property
    def address(self):
        """Address of the device. Typically used in Xcom context"""
        return self.address_or_slave

    @property
    def slave(self):
        """Slave address of the device. Typically used in Next context"""
        return self.address_or_slave

    


