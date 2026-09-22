"""
Shared Data Types 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

import logging

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any, Iterable

from .studer_dataset import StuderDatapoint


_LOGGER = logging.getLogger(__name__)


class StuderValueItem():
    datapoint: StuderDatapoint                  # Both in request and response
    code: str                                   # Both in request and response
    address_or_slave: int                       # Both in request and response
    value: Any | None                           # Only in response from request_values()
    error: str|None                             # Only in response from request_values()

    def __init__(self, datapoint: StuderDatapoint, code: str=None, address_or_slave: int=None, value: Any=None, error: str=None):

        if code is None and address_or_slave is None:
            raise StuderParamException(f"At least one of parameters 'code' or 'address_or_slave' must be specified")
        
        self.datapoint = datapoint
        self.code = code
        self.address_or_slave = address_or_slave
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


