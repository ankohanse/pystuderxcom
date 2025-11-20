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
from enum import IntEnum
import logging
import struct
from io import BufferedWriter, BufferedReader, BytesIO
from typing import Any, Iterable

from .const import (
    XcomAggregationType,
    XcomParamException,
)
from .data import (
    XcomData,
    XcomDataMultiInfoReq,
    XcomDataMultiInfoReqItem,
    XcomDataMultiInfoRsp,
    XcomDataMultiInfoRspItem,
)
from .datapoints import (
    XcomDatapoint,
    XcomDataset,
)
from .families import (
    XcomDeviceFamilies,
)


_LOGGER = logging.getLogger(__name__)


class XcomValuesItem():
    datapoint: XcomDatapoint                    # Both in request and response, for request_infos and request_values
    code: str|None                              # Both in request and response, for request_infos and request_values
    address: int|None                           # Both in request and response, for request_infos and request_values
    aggregation_type: XcomAggregationType|None  # Both in request and response, for request_infos and request_values
    value: Any                                  # Only in response from request_values()
    error: str|None                             # Only in response from request_values()

    def __init__(self, datapoint: XcomDatapoint, code:str|None=None, address:int|None=None, aggregation_type:XcomAggregationType|None=None, value:Any=None, error:str|None=None):

        # Convert from code, addr and aggr. Code trumps addr and aggr, while addr trumps aggr.
        if code is not None:
            code = code
            addr = XcomDeviceFamilies.get_addr_by_code(code)
            aggr = XcomDeviceFamilies.get_aggregationtype_by_code(code)
        
        elif address is not None:
            code = XcomDeviceFamilies.get_code_by_addr(address, datapoint.family_id)
            addr = address
            aggr = XcomDeviceFamilies.get_aggregationtype_by_addr(address)

        elif aggregation_type is not None:
            code = XcomDeviceFamilies.get_code_by_aggregationtype(aggregation_type, datapoint.family_id)
            addr = XcomDeviceFamilies.get_addr_by_aggregationtype(aggregation_type, datapoint.family_id)
            aggr = aggregation_type

        else:
            raise XcomParamException(f"One of code, addr or aggr must be passed into an XcomValuesItem")

        # Set properties
        self.datapoint = datapoint
        self.code = code
        self.address = addr
        self.aggregation_type = aggr
        self.value = value
        self.error = error


class XcomValues():
    items: Iterable[XcomValuesItem] # Both in request and response
    flags: int                      # Only in response from request_values
    datetime: int                   # Only in response from request_values

    def __init__(self, items: Iterable[XcomValuesItem], flags:int=None, datetime:int=None):
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
            items.append(XcomValuesItem(
                datapoint = dataset.get_by_nr(item.user_info_ref),
                aggregation_type = item.aggregation_type
            ))
        return XcomValues(items)

    @staticmethod
    def unpack_response(buf: bytes, req: 'XcomValues'):
        """Unpack response data"""
        rsp = XcomDataMultiInfoRsp.unpack(buf)

        # Resolve additional properties
        items = list()
        for item in rsp.items:
            datapoint = next((i.datapoint for i in req.items if i.datapoint.nr==item.user_info_ref), None)
            aggregation_type = item.aggregation_type
            value = XcomData.cast(item.data, datapoint.format) if datapoint is not None else None

            items.append(XcomValuesItem(
                datapoint = datapoint,
                aggregation_type = aggregation_type,
                value = value
            ))

        return XcomValues(items, rsp.flags, rsp.datetime)

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

