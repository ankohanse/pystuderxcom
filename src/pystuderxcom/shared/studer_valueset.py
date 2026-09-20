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


@dataclass
class StuderValueItem():
    datapoint: StuderDatapoint                  # Both in request and response
    code: str|None                              # Both in request and response
    address_or_slave: int|None                  # Both in request and response
    value: Any                                  # Only in response from request_values()
    error: str|None                             # Only in response from request_values()

    @property
    def address(self):
        return self.address_or_slave

    @property
    def slave(self):
        return self.address_or_slave


class StuderValueSet(list[StuderValueItem]):
    items: Iterable[StuderValueItem]            # Both in request and response


