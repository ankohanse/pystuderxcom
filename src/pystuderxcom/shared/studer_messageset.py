"""
Shared Data Classes 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

from enum import IntEnum
import logging

from dataclasses import dataclass

from ..shared.studer_types import (
    StuderAccess,
    StuderDataType,
    StuderTarget, 
    StuderUserLevel,
    StuderParamException,
)
from ..shared.studer_families import (
    StuderDeviceFamilies,
    StuderDeviceFamily,
    StuderDeviceFamilyUnknownException,
)

_LOGGER = logging.getLogger(__name__)


class StuderMessageUnknownException(Exception):
    pass

class StuderMessageSyntaxException(Exception):
    pass


@dataclass
class StuderMessageDef:
    level: StuderUserLevel
    number: int
    string: str


class StuderMessageSet:

    def __init__(self, messages: list[StuderMessageDef]):
        self._messages = messages


    def get_by_nr(self, nr: int) -> StuderMessageDef:
        for msg in self._messages:
            if msg.number == nr:
                return msg

        raise StuderMessageUnknownException(nr)


    def str_by_nr(self, nr: int) -> str:
        msg = self.get_by_nr(nr)
        return msg.string
