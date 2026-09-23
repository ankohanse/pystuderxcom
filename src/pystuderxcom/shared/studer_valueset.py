"""
Shared Data Types 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

import logging

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any, Iterable

from pystuderxcom.const import safe_isinstance

from ..shared.studer_dataset import StuderDatapoint
from ..shared.studer_types import StuderDiscoveredDevice, StuderParamException


_LOGGER = logging.getLogger(__name__)


class StuderValueItem():
    datapoint: StuderDatapoint      # Both in request and response
    code: str                       # Both in request and response
    address_or_slave: int           # Both in request and response (Xcom uses address, Next uses slave)
    value: Any | None               # Only in response from request_values()
    error: str|None                 # Only in response from request_values()

    def __init__(self, datapoint: StuderDatapoint, device: StuderDiscoveredDevice|int|str, value: Any=None, error: str=None):

        self.datapoint = datapoint

        # Fill the code, address or slave properties we know, rest will be determined from family in derived class
        if safe_isinstance(device, StuderDiscoveredDevice):
            self.code = device.code
            self.address_or_slave = device.address or device.slave
        elif isinstance(device, int):
            self.address_or_slave = device
            self.code = None
        elif isinstance(device, str):
            self.code = device
            self.address_or_slave = None
        else:
            raise StuderParamException(f"Parameter 'device' must be a StuderDiscoveredDevice, device address or a device code")
        
        self.value = value
        self.error = error

    @property
    def address(self):
        return self.address_or_slave

    @property
    def slave(self):
        return self.address_or_slave


class StuderValueSet():
    items: Iterable[StuderValueItem]            # Both in request and response

    def __init__(self, items: Iterable[StuderValueItem] ):
        self.items = items


