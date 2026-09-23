##
## Class implementing Xcom protocol 
##
## See the studer document: "Technical Specification - Xtender serial protocol"
## Download from:
##   https://studer-innotec.com/downloads/ 
##   -> Downloads -> software + updates -> communication protocol xcom 232i
##


import asyncio
import binascii
from dataclasses import dataclass
from enum import IntEnum
import logging
import struct
from io import BufferedWriter, BufferedReader, BytesIO
from typing import Any, Iterable

from .shared.helpers import safe_isinstance
from .shared.studer_dataset import StuderDatapoint
from .shared.studer_types import StuderDiscoveredDevice
from .shared.studer_valueset import StuderValueItem, StuderValueSet
from .const import XcomAggregationType, XcomParamException
from .data import XcomData, XcomDataMultiInfoReq, XcomDataMultiInfoReqItem, XcomDataMultiInfoRsp, XcomDataMultiInfoRspItem
from .datapoints import XcomDatapoint, XcomDataset
from .families import XcomDeviceFamilies


_LOGGER = logging.getLogger(__name__)


class XcomValueItem(StuderValueItem):
    # From parent class:
    #    datapoint: StuderDatapoint                  # Both in request and response, for request_infos and request_values
    #    code: str                                   # Both in request and response, for request_infos and request_values
    #    address_or_slave: int                       # Both in request and response, for request_infos and request_values
    #    value: Any                                  # Only in response from request_values()
    #    error: str|None                             # Only in response from request_values()

    aggregation_type: XcomAggregationType|None  # Both in request and response, for request_infos and request_values

    def __init__(self, datapoint: StuderDatapoint, device: StuderDiscoveredDevice|int|str=None, aggregation_type:XcomAggregationType=None, value:Any=None, error:str=None):

        # Convert from code, addr and aggr. Code trumps addr and aggr, while addr trumps aggr.
        families = XcomDeviceFamilies.get_instance() # singleton instance

        if safe_isinstance(device, StuderDiscoveredDevice):
            code = device.code
            addr = device.address
            aggr = families.get_aggregationtype_by_code(code)

        elif isinstance(device, int):
            addr = device
            code = families.get_code_by_addr(addr, datapoint.family_id)
            aggr = families.get_aggregationtype_by_addr(addr)

        elif isinstance(device, str):  
            code = device
            addr = families.get_addr_by_code(code)
            aggr = families.get_aggregationtype_by_code(code)

        elif isinstance(aggregation_type, XcomAggregationType):
            code = families.get_code_by_aggregationtype(aggregation_type, datapoint.family_id)
            addr = families.get_addr_by_aggregationtype(aggregation_type, datapoint.family_id)
            aggr = aggregation_type
        
        else:
            raise StuderParamException(f"Parameter 'device' or 'aggregation_type' must specified")

        # Set properties
        self.datapoint = datapoint
        self.code = code
        self.address_or_slave = addr
        self.aggregation_type = aggr
        self.value = value
        self.error = error


class XcomValueSet(StuderValueSet):
    # From parent
    #    items: Iterable[StuderValueItem] # Both in request and response
    
    flags: int                       # Only in response from request_values
    datetime: int                    # Only in response from request_values

    def __init__(self, items: Iterable[StuderValueItem], flags:int=None, datetime:int=None):
        self.items = items
        self.flags = flags
        self.datetime = datetime

    @staticmethod
    def unpack_request(buf: bytes, dataset: XcomDataset):
        """Unpack request data; only used for unit-tests"""
        req = XcomDataMultiInfoReq.unpack(buf)

        # Resolve additional properties
        items = list()
        for item in req.items:
            items.append(XcomValueItem(
                datapoint = dataset.get_by_nr(item.user_info_ref),
                aggregation_type = item.aggregation_type
            ))
        return XcomValueSet(items)

    @staticmethod
    def unpack_response(buf: bytes, req: 'XcomValueSet'):
        """Unpack response data"""
        rsp = XcomDataMultiInfoRsp.unpack(buf)

        # Resolve additional properties
        items = list()
        for item in rsp.items:
            datapoint = next((i.datapoint for i in req.items if i.datapoint.nr==item.user_info_ref), None)
            aggregation_type = item.aggregation_type
            value = XcomData.cast(item.data, datapoint.data_type) if datapoint is not None else None

            items.append(XcomValueItem(
                datapoint = datapoint,
                aggregation_type = aggregation_type,
                value = value
            ))

        return XcomValueSet(items, rsp.flags, rsp.datetime)

    def pack_request(self) -> bytes:
        """Pack a request"""
        req = XcomDataMultiInfoReq(
            items = [XcomDataMultiInfoReqItem(i.datapoint.nr, i.aggregation_type) for i in self.items]
        )
        return req.pack()
            
    def pack_response(self) -> bytes:
        """Pack a response; only used for unit-testing"""
        rsp = XcomDataMultiInfoRsp(
            flags = self.flags,
            datetime = self.datetime,
            items = [XcomDataMultiInfoRspItem(i.datapoint.nr, i.aggregation_type, float(i.value)) for i in self.items]
        )
        return rsp.pack()

