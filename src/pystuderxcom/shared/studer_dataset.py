"""
Shared Data Classes 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

from enum import IntEnum
import logging

from dataclasses import dataclass

from ..shared.helpers import safe_isinstance
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


class StuderDatapointUnknownException(Exception):
    pass

class StuderDatapointSyntaxException(Exception):
    pass

class StuderDatapointEnumNotFoundException(Exception):
    pass


@dataclass
class StuderDatapoint:
    family_id: str
    parent_id: str | None
    id: str
    userlevel_r: StuderUserLevel
    userlevel_w: StuderUserLevel
    nr_or_addr: int         # nr in Xcom, addr in Next
    name: str
    label: str   # abbreviated/coded name
    unit: str
    data_type: StuderDataType
    size: int
    access: StuderAccess
    target: StuderTarget
    default: float|str = None
    min: float|str = None
    max: float|str = None
    inc: float|str = None
    enum_id: str = None
    enum_options: dict = None

    @property
    def nr(self) -> int:
        """In Xcom context, a datapoint is identified by family and nr"""
        return self.nr_or_addr

    @property
    def address(self) -> int:
        """In Next context, a datapoint is identified by family and address"""
        return self.nr_or_addr


    def enum_value(self, key):
        if self.data_type not in [StuderDataType.ENUM16, StuderDataType.ENUM32]:
            return None
        
        key = str(key)
        if not isinstance(self.enum_options, dict) or key not in self.enum_options:
            return key
        else:
            return self.enum_options[key]

    
    def enum_key(self, value):
        if self.data_type not in [StuderDataType.ENUM16, StuderDataType.ENUM32]:
            return None
        
        if not isinstance(self.enum_options, dict) or value not in self.enum_options.values():
            return None
        else:
            key = next((key for key,val in self.enum_options.items() if val==value), None)
            return int(key)


    def bitfield_value(self, bits:list[bool]):
        if self.data_type not in [StuderDataType.BITFIELD]:
            return None

        if not isinstance(bits, list):
            raise StuderParamException(f"Unexpected key {bits} ({type(bits)}) while decoding bitfield; family={self.family_id}, address={self.address}, type={self.data_type}")

        result = []
        if not any(bits):
            result.append( self.enum_options.get('0', None) )
        else:
            key = 1
            for bit in bits:
                if bit:
                    result.append( self.enum_options.get(str(key), None) )
                key = key * 2

        return list(filter(None, result))


class StuderDataset:

    def __init__(self, datapoints: list[StuderDatapoint], families: StuderDeviceFamilies):
        self._datapoints = datapoints
        self._families = families


    def get_by_id(self, id: str, family: StuderDeviceFamily|str|int = None) -> StuderDatapoint:
        """
        Find a datapoint by family and id.
        Family can be omitted as all ids are unique (no overlap between families).
        Can be used in both Xcom and Next context.
        """
        if id is None:
            raise StuderParamException(f"Parameter 'id' must be provided in call to get_by_id")

        if safe_isinstance(family, StuderDeviceFamily):
            family_id = family.id
        elif isinstance(family, str):
            family_id = self._families.get_by_id(family).id
        else:
            family_id = None

        for point in self._datapoints:
            if point.id == id and (point.family_id == family_id or family_id is None):
                return point

        raise StuderDatapointUnknownException(id, family_id)
    

    def get_by_nr(self, nr: int, family: StuderDeviceFamily|str=None) -> StuderDatapoint:
        """
        Find a datapoint by family and nr.
        Typically uses in Xcom context (Next uses address instead of nr)
        """
        if nr is None:
            raise StuderParamException(f"Parameter 'nr' must be provided in call to get_by_nr")
        if family is None:
            raise StuderParamException(f"Parameter 'family' must be provided in call to get_by_nr")

        return self._get_by_nr_or_address(nr, family)

    def get_by_address(self, address: int, family: StuderDeviceFamily|str=None) -> StuderDatapoint:
        """
        Find a datapoint by family and address.
        Typically uses in Next context (Xcom uses nr instead of address)
        """
        if address is None:
            raise StuderParamException(f"Parameter 'address' must be provided in call to get_by_address")
        if family is None:
            raise StuderParamException(f"Parameter 'family' must be provided in call to get_by_address")

        return self._get_by_nr_or_address(address, family)

    def _get_by_nr_or_address(self, nr_or_addr: int, family: StuderDeviceFamily|str=None) -> StuderDatapoint:
        """
        Find a datapoint by family combined with nr or address.
        Can be used in both Xcom and Next context; Xcom uses its own overridden version of this function.
        """
        if nr_or_addr is None:
            raise StuderParamException(f"Parameter 'nr_or_addr' must be provided in call to _get_by_nr_or_address")
        if family is None:
            raise StuderParamException(f"Parameter 'family' must be provided in call to _get_by_nr_or_address")

        if safe_isinstance(family, StuderDeviceFamily):
            family_id = family.id
        elif isinstance(family, str):
            family_id = family
        else:
            raise StuderParamException(f"Parameter 'family' must be a StuderDeviceFamily or a family_id")

        for point in self._datapoints:
            if point.nr_or_addr == nr_or_addr and point.family_id == family_id:
                return point

        raise StuderDatapointUnknownException(nr_or_addr, family_id)
        

    def get_menu_items(self, family: StuderDeviceFamily|str, parent_id: str = ""):

        if safe_isinstance(family, StuderDeviceFamily):
            family_id = family.id
        elif isinstance(family, str):
            family_id = family
        else:
            raise StuderParamException(f"Parameter 'family_id' must be provided in call to 'get_menu_items'")

        # Xcom uses "0" as root parent_id, while Next uses ""
        parent_ids = [parent_id] if parent_id else ["","0"]

        datapoints = []
        for point in self._datapoints:
            if point.family_id == family_id and point.parent_id in parent_ids:
                datapoints.append(point)

        return datapoints

