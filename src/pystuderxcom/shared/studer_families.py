"""
Shared Data Classes 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

from enum import IntEnum
import logging

from dataclasses import dataclass

from .studer_types import (
    StuderAccess,
    StuderDataType,
    StuderTarget, 
    StuderUserLevel,
    StuderParamException,
)


_LOGGER = logging.getLogger(__name__)


class StuderDeviceFamilyUnknownException(Exception):
    pass

class StuderDeviceCodeUnknownException(Exception):
    pass

class StuderDeviceAddressUnknownException(Exception):
    pass

class StuderDeviceSlaveUnknownException(Exception):
    pass


@dataclass
class StuderDeviceFamily():
    id: str                 # Short id
    model: str              # Model name

    def get_code(self, addr_or_slave):
        raise NotImplementedError("Function get_code must be implemented in derived class")

    def __str__(self):
        return self.id
    
    def __repr__(self):
        return self.id


class StuderDeviceFamilies(list[StuderDeviceFamily]):

    def __init__(self, families: list[StuderDeviceFamily] | None = None):
        super().__init__(families)

    def get_by_id(self, id: str) -> StuderDeviceFamily:
        for f in self:
            if f.id == id:
                return f

        raise StuderDeviceFamilyUnknownException(id)

    @staticmethod
    def get_by_code(code: str) -> StuderDeviceFamily:
        raise NotImplementedError("Function get_code must be implemented in derived class")

