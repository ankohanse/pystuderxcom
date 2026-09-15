##
# Definition of all known device families used in the Xcom protocol
##

import logging

from dataclasses import dataclass
from typing import Any

from .shared.studer_families import (
    StuderDeviceFamilies,
    StuderDeviceFamily,
    StuderDeviceFamilyUnknownException,
    StuderDeviceAddressUnknownException,
)
from .const import (
    XcomAggregationType,
    XcomParamException,
) 


_LOGGER = logging.getLogger(__name__)


@dataclass
class XcomDeviceFamily(StuderDeviceFamily):
    # From super class
    id: str
    model: str

    # Specific for xcom device family
    id_for_nr: str    # L1, L2 and L3 use xt numbers
    addr_multicast: int
    addr_devices_start: int
    addr_devices_end: int
    nr_params_start: int
    nr_params_end: int
    nr_infos_start: int
    nr_infos_end: int
    nr_discover: int
    nr_id_type: int | None
    nr_id_hw_cmd: int | None
    nr_id_hw_pwr: int | None
    nr_id_sw_msb: int | None
    nr_id_sw_lsb: int | None
    nr_id_fid_msb: int | None
    nr_id_fid_lsb: int | None

    def get_code(self, addr):
        if addr == self.addr_multicast:
            return self.id.upper()
        
        if self.addr_devices_start == addr == self.addr_devices_end:
            return self.id.upper()
        
        if self.addr_devices_start <= addr <= self.addr_devices_end:
            idx = addr - self.addr_devices_start + 1
            return f"{self.id.upper()}{idx}"
        
        msg = f"Addr {addr} is not in range for family {self.id} addresses ({self.addr_devices_start}-{self.addr_devices_end})"
        raise StuderDeviceAddressUnknownException(msg)

    def __str__(self):
        return self.id
    
    def __repr__(self):
        return self.id


class XcomDeviceFamilies(StuderDeviceFamilies):

    # Static known families
    XTENDER = XcomDeviceFamily(
        "xt",                  # id
        "Xtender",             # model
        "xt",                  # id for nr
        100,                   # addr multicast to all devices (write only)
        101, 109,              # addr devices,  start to end
        1000, 1999,            # nr for params, start to end
        3000, 3999,            # nr for infos,  start to end 
        3000,                  # nr for discovery
        3124,                  # nr for model/type    
        3129, 3132,            # nr for hardware version (cmd, pwr)
        3130, 3131,            # nr for software version (msb, lsb)
        3156, 3157,            # nr for fid (msb, lsb)
    )
    L1 = XcomDeviceFamily(
        "l1",                  # id
        "Phase L1",            # model
        "xt",                  # id for nr
        191,                   # addr multicast to all devices (write only)
        191, 191,              # addr devices,  start to end
        1000, 1999,            # nr for params, start to end
        3000, 3999,            # nr for infos,  start to end   
        3000,                  # nr for discovery
        None,                  # nr for model/type    
        None, None,            # nr for hardware version (cmd, pwr)
        None, None,            # nr for software version (msb, lsb)
        None, None,            # nr for fid (msb, lsb)
    )
    L2 = XcomDeviceFamily(
        "l2",                  # id
        "Phase L2",            # model
        "xt",                  # id for nr
        192,                   # addr multicast to all devices (write only)
        192, 192,              # addr devices,  start to end
        1000, 1999,            # nr for params, start to end
        3000, 3999,            # nr for infos,  start to end   
        3000,                  # nr for discovery
        None,                  # nr for model/type    
        None, None,            # nr for hardware version (cmd, pwr)
        None, None,            # nr for software version (msb, lsb)
        None, None,            # nr for fid (msb, lsb)
    )
    L3 = XcomDeviceFamily(
        "l3",                  # id
        "Phase L3",            # model
        "xt",                  # id for nr
        193,                   # addr multicast to all devices (write only)
        193, 193,              # addr devices,  start to end
        1000, 1999,            # nr for params, start to end
        3000, 3999,            # nr for infos,  start to end   
        3000,                  # nr for discovery
        None,                  # nr for model/type    
        None, None,            # nr for hardware version (cmd, pwr)
        None, None,            # nr for software version (msb, lsb)
        None, None,            # nr for fid (msb, lsb)
    )
    RCC = XcomDeviceFamily(
        "rcc",                 # id
        "RCC",                 # model
        "rcc",                 # id for nr
        500,                   # addr multicast to all devices (write only)
        501, 501,              # addr devices,  start to end
        5000, 5999,            # nr for params, start to end
        0, 0,                  # nr for infos,  start to end
        5002,                  # nr for discovery
        None,                  # nr for model/type    
        None, None,            # nr for hardware version (cmd, pwr)
        None, None,            # nr for software version (msb, lsb)
        None, None,            # nr for fid (msb, lsb)
    )
    BMS = XcomDeviceFamily(
        "bms",                 # id
        "Xcom-CAN BMS",        # model
        "bms",                 # id for nr
        600,                   # addr multicast to all devices (write only)
        601, 601,              # addr devices,  start to end
        6000, 6999,            # nr for params, start to end
        7000, 7999,            # nr for infos,  start to end
        7054,                  # nr for discovery
        7034,                  # nr for model/type    
        7036, None,            # nr for hardware version (cmd, pwr)
        7037, 7038,            # nr for software version (msb, lsb)
        7048, 7049,            # nr for fid (msb, lsb)
    )
    BSP = XcomDeviceFamily(    # Place AFTER BMS; during Discovery BSP is only tested if no BMS is found
        "bsp",                 # id
        "BSP",                 # model
        "bsp",                 # id for nr
        600,                   # addr multicast to all devices (write only)
        601, 601,              # addr devices,  start to end
        6000, 6999,            # nr for params, start to end
        7000, 7999,            # nr for infos,  start to end
        7034,                  # nr for discovery
        7034,                  # nr for model/type    
        7036, None,            # nr for hardware version (cmd, pwr)
        7037, 7038,            # nr for software version (msb, lsb)
        7048, 7049,            # nr for fid (msb, lsb)
    )
    VARIOTRACK = XcomDeviceFamily(
        "vt",                  # id
        "VarioTrack",          # model
        "vt",                  # id for nr
        300,                   # addr multicast to all devices (write only)
        301, 315,              # addr devices,  start to end
        10000, 10999,          # nr for params, start to end
        11000, 11999,          # nr for infos,  start to end
        11000,                 # nr for discovery
        11047,                 # nr for model/type    
        11049, None,           # nr for hardware version (cmd, pwr)
        11050, 11051,          # nr for software version (msb, lsb)
        11067, 11068,          # nr for fid (msb, lsb)
    )
    VARIOSTRING = XcomDeviceFamily(
        "vs",                  # id
        "VarioString",         # model
        "vs",                  # id for nr
        700,                   # addr multicast to all devices (write only)
        701, 715,              # addr devices,  start to end
        14000, 14999,          # nr for params, start to end
        15000, 15999,          # nr for infos,  start to end
        15000,                 # nr for discovery
        15074,                 # nr for model/type    
        15076, None,           # nr for hardware version (cmd, pwr)
        15077, 15078,          # nr for software version (msb, lsb)
        15102, 15103,          # nr for fid (msb, lsb)
    )   
    XCOM = XcomDeviceFamily(   # virtual device to expose additional values in a uniform way
        "xcom",                # id 
        "Xcom-LAN/232i",       # model
        "xcom",                # id for nr
        990,                   # addr multicast to all devices (write only)
        990, 990,              # addr devices,  start to end
        98000, 98999,          # nr for params, start to end
        99000, 99999,          # nr for infos,  start to end 
        99000,                 # nr for discovery
        None,                  # nr for model/type    
        None, None,            # nr for hardware version (cmd, pwr)
        None, None,            # nr for software version (msb, lsb)
        None, None,            # nr for fid (msb, lsb)
    )


    def __init__(self, list: list[XcomDeviceFamily]):
        super().__init__(list)

        # Fill helper variables once"""
        self._code_to_family_map: dict[str,XcomDeviceFamily] = {}
        self._code_to_addr_map: dict[str,int] = {}
        self._code_to_aggr_map: dict[int,XcomAggregationType] = {}
        self._addr_to_aggr_map: dict[str,int] = {}
        # Note: no _addr_to_code_map because address range for BMS and BSP overlap

        for f in self:
            has_aggr = f not in [XcomDeviceFamilies.L1, XcomDeviceFamilies.L2, XcomDeviceFamilies.L3]

            for addr in range(f.addr_devices_start, f.addr_devices_end+1):
                code = f.get_code(addr)
                aggr = XcomAggregationType(addr - f.addr_devices_start + 1) if has_aggr else None
                
                self._code_to_family_map[code] = f
                self._code_to_addr_map[code] = addr # XT1-XT9 -> 101-109,  VT1-VT15 -> 301-315,  VS1-VS15 -> 701-715
                self._code_to_aggr_map[code] = aggr # XT1-XT9 -> 1-9,      VT1-VT15 -> 1-15,     VS1-VS15 -> 1-15
                self._addr_to_aggr_map[addr] = aggr # 101-109 -> 1-9,      301-315  -> 1-15,     701-715  -> 1-15


    def get_by_id(self, id: str) -> XcomDeviceFamily:
        """
        Lookup the id to find the device family
        """
        return super().get_by_id(id)


    def get_by_code(self, code: str) -> XcomDeviceFamily:
        """
        Lookup the code to find the device family
        """
        return  self._code_to_family_map.get(code, None)
    

    def get_addr_by_code(self, code: str) -> int:
        """
        Lookup the code to find the addr
        """
        return self._code_to_addr_map.get(code, None)


    def get_aggregationtype_by_code(self, code: str) -> XcomAggregationType:
        """
        Lookup the code to find the aggregation_type
        """
        return self._code_to_aggr_map.get(code, None)


    def get_code_by_addr(self, addr: int, family_id: str) -> int:
        """
        Lookup the addr to find the code.
        Family is passed as hint because BMS and BSP use same address range
        """
        for family in self:
            if family.id == family_id or family.id_for_nr == family_id:
                try:
                    return family.get_code(addr)
                except:
                    pass
        
        return None


    def get_aggregationtype_by_addr(self, addr: int) -> XcomAggregationType:
        """
        Lookup the device address to find the aggregation_type
        Note that addr 601 can either be BMS or BSP. However, both result in XcomAggregationType=1 so we don't care...
        """
        return self._addr_to_aggr_map.get(addr, None)
    

    def get_code_by_aggregationtype(self, aggr: XcomAggregationType, family_id: str):
        """
        Reverse lookup an aggregation_type to find the corresponding device code within a family
        Note that some aggregation_types (AVERAGE,SUM) will result in a None response.
        """
        addr = self.get_addr_by_aggregationtype(aggr, family_id)
        if addr is not None:
            return self.get_code_by_addr(addr, family_id)
        else:
            return None
        

    def get_addr_by_aggregationtype(self, aggr: XcomAggregationType, family_id: str):
        """
        Reverse lookup an aggregation_type to find the corresponding device address within a family.
        Note that some aggregation_types (AVERAGE,SUM) will result in a None response.
        """
        family = self.get_by_id(family_id)

        for addr in range(family.addr_devices_start, family.addr_devices_end+1):
            if self._addr_to_aggr_map.get(addr, None) == aggr:
                return addr
            
        return None
