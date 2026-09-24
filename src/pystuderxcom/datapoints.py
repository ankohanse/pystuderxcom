#! /usr/bin/env python3

##
# Definition of all parameters / constants used in the Xcom protocol
##

import decimal
import logging
import orjson

from aiofiles import open as aiofiles_open
from dataclasses import dataclass
from enum import StrEnum


from .shared.helpers import (
    HybridLock,
    safe_isinstance,
)
from .shared.studer_families import (
    StuderDeviceFamily,
)
from .shared.studer_types import (
    StuderAccess, 
    StuderDataType, 
    StuderTarget, 
    StuderUserLevel,
    StuderParamException,
)
from .shared.studer_dataset import (
    StuderDatapointUnknownException,
    StuderDataset,
    StuderDatapoint,
    StuderDatapointSyntaxException
)
from .const import (
    XcomUserLevel,
    XcomVoltage,
)
from .families import (
    XcomDeviceFamilies,
)


_LOGGER = logging.getLogger(__name__)


@dataclass
class XcomDatapoint(StuderDatapoint):

    NR_VIRTUAL_START = 98000
    NR_VIRTUAL_END = 99999

    @staticmethod
    def from_dict(d) -> StuderDatapoint:
        fam = d.get('fam', None)
        lvl = d.get('lvl', None)
        pnr = d.get('pnr', None)
        nr  = d.get('nr', None)
        name = d.get('name', None)
        short = d.get('short', None) # Not used
        unit = d.get('unit', None)
        fmt = d.get('fmt', None)
        dft = d.get('def', None)
        min = d.get('min', None)
        max = d.get('max', None)
        inc = d.get('inc', None)
        opt = d.get('opt', None)

        # Check and convert properties
        if "_rem" in d and len(d)==1:
            return None # Line only contains a comment
        
        if not fam or not lvl or not nr or not name or not fmt:
            raise StuderDatapointSyntaxException(f"Missing required field in dataset; fam={fam}, lvl={lvl}, nr={nr}, name={name}, fmt={fmt}")
        
        if not isinstance(nr, int) or not isinstance(pnr, int):
            raise StuderDatapointSyntaxException(f"Unexpected field type in dataset, expected int; fam={fam}, nr={nr}, pnr={pnr}")
        
        family_id = str(fam)
        parent_id = str(pnr)
        id = str(nr)
        user_level = XcomUserLevel.from_str(str(lvl))
        number = int(nr)
        name = str(name).strip()
        unit = unit if type(unit) is str else None
        data_type = XcomDatapoint._resolve_datatype(str(fmt))
        default = float(dft) if (type(dft) is int or type(dft) is float) else "S" if (dft=="S") else None
        minimum = float(min) if (type(min) is int or type(min) is float) else "S" if (dft=="S") else None
        maximum = float(max) if (type(max) is int or type(max) is float) else "S" if (dft=="S") else None
        increment = float(inc) if (type(inc) is int or type(inc) is float) else "S" if (dft=="S") else None
        options = opt if type(opt) is dict else None
        access = XcomDatapoint._resolve_accesss(number, user_level, default)
        target = XcomDatapoint._resolve_target(number)
            
        return StuderDatapoint(
            family_id = family_id, 
            parent_id = parent_id, 
            id = id,
            userlevel_r = user_level, 
            userlevel_w = user_level, 
            nr_or_addr = number, 
            name = name, 
            label = name, 
            unit = unit, 
            data_type = data_type, 
            size = None,
            access = access,
            target = target,
            default = default, 
            min = minimum, 
            max = maximum, 
            inc = increment,
            enum_id = None,
            enum_options = options
        )


    @classmethod
    def _resolve_accesss(cls, nr, user_level, default) -> StuderAccess:
        if user_level in [StuderUserLevel.INFO]:
            return StuderAccess.READ

        if user_level in [StuderUserLevel.VIEWONLY, StuderUserLevel.BASIC, StuderUserLevel.EXPERT, StuderUserLevel.INSTALLER, StuderUserLevel.STUDER]:
            if default in ['S']:
                return StuderAccess.WRITE   # used for Signal
            else:
                return StuderAccess.READ_WRITE
            
        _LOGGER.debug(f"Unknown user-level for datapoint {nr} with level {user_level}")
        return StuderAccess.READ


    @classmethod
    def _resolve_target(cls, nr) -> StuderTarget:
        if XcomDatapoint.NR_VIRTUAL_START <= nr <= XcomDatapoint.NR_VIRTUAL_END:
            return StuderTarget.VIRTUAL
        else:
            return StuderTarget.STANDARD


    @classmethod
    def _resolve_datatype(cls, s: str, default: StuderDataType = None) -> StuderDataType:
        match s.upper():
            case 'BOOL': return StuderDataType.BOOL
            case 'FORMAT': return StuderDataType.FORMAT
            case 'SHORT_ENUM' | 'SHORT ENUM': return StuderDataType.ENUM16
            case 'ERROR': return StuderDataType.ERROR
            case 'INT32': return StuderDataType.INT32
            case 'FLOAT': return StuderDataType.FLOAT32
            case 'LONG_ENUM' | 'LONG ENUM': return StuderDataType.ENUM32
            case 'GUID': return StuderDataType.GUID
            case 'STRING': return StuderDataType.STRING
            case 'DYNAMIC': return StuderDataType.DYNAMIC
            case 'MENU' | 'ONLY_LEVEL' | 'ONLY LEVEL': return StuderDataType.MENU
            case 'NOT SUPPORTED': return StuderDataType.INVALID
            case _: 
                if default is not None:
                    return default
                else:
                    msg = f"Unknown format: '{s}'"
                    raise Exception(msg)


class XcomDataset(StuderDataset):

    PATH_120V = __file__.replace('.py', '_120v.json')
    PATH_240V = __file__.replace('.py', '_240v.json')
    PATH_XCOM = __file__.replace('.py', '_xcom.json')


    def __init__(self):
        raise RuntimeError("Use 'XcomDataset.get_instance()' or 'await XcomDataset.async_get_instance()' instead of direct instantiation.")

    # Single instance of the XcomDataset
    _instance = None
    _instance_lock = HybridLock()

    @classmethod
    async def async_get_instance(cls, voltageAC:str=XcomVoltage.AC240, voltageDC:str=XcomVoltage.DC48, flags:dict=None) -> 'XcomDataset':
        """
        Async helper function to get singleton instance of XcomDataset
        """
        async with cls._instance_lock:
            if cls._instance is None:
                # Create a bare instance without calling __init__
                self = super().__new__(cls)
                await self._async_init(voltageAC, voltageDC, flags)
                cls._instance = self

        return cls._instance

    @classmethod
    def get_instance(cls, voltageAC:str=XcomVoltage.AC240, voltageDC:str=XcomVoltage.DC48, flags:dict=None) -> 'XcomDataset':
        """
        Sync helper function to get singleton instance of XcomDataset
        """
        with cls._instance_lock:
            if cls._instance is None:
                # Create a bare instance without calling __init__
                self = super().__new__(cls)
                self._init(voltageAC, voltageDC, flags)
                cls._instance = self
            
        return cls._instance

    @classmethod
    def del_instance(cls):
        """Used for intermediate cleanup during unit tests"""
        cls._instance = None


    async def _async_init(self, voltageAC:str=XcomVoltage.AC240, voltageDC:str=XcomVoltage.DC48, flags:dict=None):
        """
        Perform the actual async initialization
        """
        flags = flags or {}

        async with aiofiles_open(XcomDataset.PATH_120V, "r", encoding="UTF-8") as file_120vac:
            text_120vac = await file_120vac.read()
        async with aiofiles_open(XcomDataset.PATH_240V, "r", encoding="UTF-8") as file_240vac:
            text_240vac = await file_240vac.read()
        async with aiofiles_open(XcomDataset.PATH_XCOM, "r", encoding="UTF-8") as file_xcom:
            text_xcom = await file_xcom.read()
        
        values_120vac = orjson.loads(text_120vac)
        values_240vac = orjson.loads(text_240vac)
        values_xcom   = orjson.loads(text_xcom)

        datapoints = self._get_datapoints_from_values(voltageAC, voltageDC, values_120vac, values_240vac, values_xcom)
        families = await XcomDeviceFamilies.async_get_instance() # singleton instance

        _LOGGER.info(f"Using {len(datapoints)} datapoints")
        super().__init__(datapoints, families)


    def _init(self, voltageAC:str=XcomVoltage.AC240, voltageDC:str=XcomVoltage.DC48, flags:dict=None):
        """
        Perform the actual async initialization
        """
        flags = flags or {}

        with open(XcomDataset.PATH_120V, "r", encoding="UTF-8") as file_120vac:
            text_120vac = file_120vac.read()
        with open(XcomDataset.PATH_240V, "r", encoding="UTF-8") as file_240vac:
            text_240vac = file_240vac.read()
        with open(XcomDataset.PATH_XCOM, "r", encoding="UTF-8") as file_xcom:
            text_xcom = file_xcom.read()
        
        values_120vac = orjson.loads(text_120vac)
        values_240vac = orjson.loads(text_240vac)
        values_xcom   = orjson.loads(text_xcom)

        datapoints = self._get_datapoints_from_values(voltageAC, voltageDC, values_120vac, values_240vac, values_xcom)
        families = XcomDeviceFamilies.get_instance() # singleton instance

        _LOGGER.info(f"Using {len(datapoints)} datapoints")
        super().__init__(datapoints, families)


    def _get_datapoints_from_values(self, voltageAC, voltageDC, values_120vac, values_240vac, values_xcom):
        """
        """
        datapoints_120vac = list(filter(None, [XcomDatapoint.from_dict(val) for val in values_120vac]))
        datapoints_240vac = list(filter(None, [XcomDatapoint.from_dict(val) for val in values_240vac]))
        datapoints_xcom   = list(filter(None, [XcomDatapoint.from_dict(val) for val in values_xcom]))

        # start with the merged 240v + xcom lists as base
        datapoints = datapoints_240vac + datapoints_xcom

        match voltageAC:
            case XcomVoltage.AC240:
                pass
            case XcomVoltage.AC120:
                # Merge the 120v list into the 240v one by replacing duplicates. This maintains the order of menu items
                for dp120 in datapoints_120vac:
                    # already in result?
                    index = next( (idx for idx,dp240 in enumerate(datapoints) if dp120.nr == dp240.nr and dp120.family_id == dp240.family_id ), None)
                    if index is not None:
                        datapoints[index] = dp120
            case _:
                msg = f"Unknown AC voltage: '{voltageAC}'"
                raise Exception(msg)
        
        # Standard list is for 48vdc. Adapt for 12 or 24vdc if needed.
        match voltageDC:
            case XcomVoltage.DC48: mult = 1.0
            case XcomVoltage.DC24: mult = 0.5
            case XcomVoltage.DC12: mult = 0.25
            case _: 
                msg = f"Unknown DC voltage: '{voltageDC}'"
                raise Exception(msg)
            
        for idx,dp in enumerate(datapoints):
            if dp.unit=="Vdc" and \
               dp.min is not None and dp.min > 24.0 and \
               dp.max is not None and dp.max < 96.0:

                d = decimal.Decimal(str(dp.inc)) if dp.inc is not None else decimal('1')
                digits = d.as_tuple().exponent * -1

                dp.default = round(mult * dp.default, digits) if dp.default is not None else None
                dp.min     = round(mult * dp.min    , digits) if dp.min     is not None else None
                dp.max     = round(mult * dp.max    , digits) if dp.max     is not None else None
                datapoints[idx] = dp

        return datapoints


    def get_by_nr(self, nr: int, family: StuderDeviceFamily|str=None) -> StuderDatapoint:
        """
        Find a datapoint by family and nr.
        In Xcom context, Family can be omitted as all numbers are unique (no overlap between families).
        """
        if nr is None:
            raise StuderParamException(f"Parameter 'nr' must be provided in call to get_by_nr")

        # Carefully determine family id for lookup as families L1,L2 and L3 use datapoints from xt
        if safe_isinstance(family, StuderDeviceFamily):
            family_id = family.id_for_nr if hasattr(family, 'id_for_nr') else family.id
        elif isinstance(family, str):
            family = self._families.get_by_id(family)
            family_id = family.id_for_nr if hasattr(family, 'id_for_nr') else family.id
        else:
            family_id = None

        for point in self._datapoints:
            if point.nr == nr and (point.family_id == family_id or family_id is None):
                return point

        raise StuderDatapointUnknownException(nr, family_id)
    

