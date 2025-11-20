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
import io
import logging
import struct

from io import BufferedWriter, BufferedReader, BytesIO

from .const import (
    XcomFormat,
    ScomAddress,
    ScomErrorCode,
)
from .data import (
    XcomData,
    read_float,
    write_float,
    read_uint32,
    write_uint32,
    read_uint16,
    write_uint16,
    read_uint8,
    write_uint8,
    read_sint32,
    write_sint32,
    read_bytes,
    write_bytes,
)


_LOGGER = logging.getLogger(__name__)


class XcomService:

    object_type: int
    object_id: int
    property_id: int
    property_data: bytes

    @staticmethod
    def parse(f: BufferedReader):
        return XcomService(
            object_type   = read_uint16(f),
            object_id     = read_uint32(f),
            property_id   = read_uint16(f),
            property_data = read_bytes(f, -1),
        )

    def __init__(self, 
            object_type: int, object_id: int, 
            property_id: int, property_data: bytes):

        self.object_type = object_type
        self.object_id = object_id
        self.property_id = property_id
        self.property_data = property_data

    def assemble(self, f: BufferedWriter):
        write_uint16(f, self.object_type)
        write_uint32(f, self.object_id)
        write_uint16(f, self.property_id)
        write_bytes(f, self.property_data)

    def __len__(self) -> int:
        return 2*2 + 4 + len(self.property_data)

    def __str__(self) -> str:
        return f"Service(obj_type={self.object_type:04X}, obj_id={self.object_id}, property_id={self.property_id:02X}, property_data={self.property_data.hex(' ',1)})"


class XcomFrame:

    service_flags: int
    service_id: int
    service_data: XcomService

    @staticmethod
    def parse(f: BufferedReader):
        return XcomFrame(
            service_flags = read_uint8(f),
            service_id = read_uint8(f),
            service_data = XcomService.parse(f)
        )

    @staticmethod
    def parse_bytes(buf: bytes):
        return XcomFrame.parse(BytesIO(buf))

    def __init__(self, service_id: bytes, service_data: XcomService, service_flags=0):
        self.service_flags = service_flags
        self.service_id = service_id
        self.service_data = service_data

    def assemble(self, f: BufferedWriter):
        write_uint8(f, self.service_flags)
        write_uint8(f, self.service_id)
        self.service_data.assemble(f)

    def get_bytes(self) -> bytes:
        buf = BytesIO()
        self.assemble(buf)
        return buf.getvalue()

    def __len__(self) -> int:
        return 2*1 + len(self.service_data)

    def __str__(self) -> str:
        return f"Frame(flags={self.service_flags:01X}, id={self.service_id:01X}, service={self.service_data})"


class XcomHeader:

    frame_flags: int
    src_addr: int
    dst_addr: int
    data_length: int

    length: int = 1 + 4 + 4 + 2

    @staticmethod
    def parse(f: BufferedReader):
        return XcomHeader(
            frame_flags = read_uint8(f),
            src_addr = read_uint32(f),
            dst_addr = read_uint32(f),
            data_length = read_uint16(f)
        )

    @staticmethod
    def parse_bytes(buf: bytes):
        return XcomHeader.parse(BytesIO(buf))

    def __init__(self, src_addr: int, dst_addr: int, data_length: int, frame_flags=0):
        assert frame_flags >= 0, "frame_flags must not be negative"

        self.frame_flags = frame_flags
        self.src_addr = src_addr
        self.dst_addr = dst_addr
        self.data_length = data_length

    def assemble(self, f: BufferedWriter):
        write_uint8(f, self.frame_flags)
        write_uint32(f, self.src_addr)
        write_uint32(f, self.dst_addr)
        write_uint16(f, self.data_length)

    def get_bytes(self) -> bytes:
        buf = BytesIO()
        self.assemble(buf)
        return buf.getvalue()

    def __len__(self) -> int:
        return self.length

    def __str__(self) -> str:
        return f"Header(flags={self.frame_flags}, src={self.src_addr}, dst={self.dst_addr}, data_length={self.data_length})"


class XcomPackage():

    max_length = 256 # from Studer Xcom documentation
    start_byte: bytes = b'\xAA'
    delimeters: bytes = b'\x0D\x0A'
    header: XcomHeader
    frame_data: XcomFrame

    @staticmethod
    def gen_package(
            service_id: int,
            object_type: int,
            object_id: int,
            property_id: int,
            property_data: bytes,
            src_addr = ScomAddress.SOURCE,
            dst_addr = ScomAddress.BROADCAST):
        
        service = XcomService(object_type, object_id, property_id, property_data)
        frame = XcomFrame(service_id, service)
        header = XcomHeader(src_addr, dst_addr, len(frame))

        return XcomPackage(header, frame)

    def __init__(self, header: XcomHeader, frame_data: XcomFrame):
        self.header = header
        self.frame_data = frame_data

    def assemble(self, f: BufferedWriter):
        write_bytes(f, self.start_byte)

        header = self.header.get_bytes()
        write_bytes(f, header)
        write_bytes(f, XcomPackage.checksum(header))

        data = self.frame_data.get_bytes()
        write_bytes(f, data)
        write_bytes(f, XcomPackage.checksum(data))

        # Don't write delimeter, seems not needed as we send the package in one whole chunk
        #write_bytes(f, self.delimeters)

    def get_bytes(self) -> bytes:
        buf = BytesIO()
        self.assemble(buf)
        return buf.getvalue()
    
    def is_response(self) -> bool:
        return (self.frame_data.service_flags & 2) >> 1 == 1

    def is_error(self) -> bool:
        return self.frame_data.service_flags & 1 == 1

    def get_error(self) -> str:
        if self.is_error():
            error = XcomData.unpack(self.frame_data.service_data.property_data, XcomFormat.ERROR)
            return ScomErrorCode.get_by_error(error)
        return None
 
    def __str__(self) -> str:
        return f"Package(header={self.header}, frame={self.frame_data})"


    @staticmethod
    def checksum(data: bytes) -> bytes:
        """Function to calculate the checksum needed for the header and the data"""
        A = 0xFF
        B = 0x00

        for d in data:
            A = (A + d) % 0x100
            B = (B + A) % 0x100

        A = struct.pack("<B", A)
        B = struct.pack("<B", B)

        return A + B

