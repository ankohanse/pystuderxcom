#! /usr/bin/env python3

##
# Definition of all parameters / constants used in the Xcom protocol
##

import logging

from dataclasses import dataclass

from .shared.studer_types import (
    StuderAccess, 
    StuderDataType, 
    StuderTarget, 
    StuderUserLevel,
)
from .shared.studer_dataset import (
    StuderDataset,
    StuderDatapoint,
    StuderDatapointSyntaxException
)
from .const import (
    XcomUserLevel,
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

