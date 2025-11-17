#! /usr/bin/env python3

##
# Definition of all parameters / constants used in the Xcom protocol
##

import asyncio
import binascii
from datetime import datetime, timedelta
import logging
import orjson

from aiofiles import open as aiofiles_open
from io import BufferedReader

from .const import (
    REQ_TIMEOUT,
    XcomVoltage
)
from .data import (
    AsyncReader,
    SyncReader,
    readBytes
)
from .datapoints import (
    XcomDatapoint,
    XcomDataset,
)
from .messages import (
    XcomMessageDef, 
    XcomMessageSet,
)
from .protocol import (
    XcomFrame, 
    XcomHeader, 
    XcomPackage,
)


_LOGGER = logging.getLogger(__name__)


class AsyncXcomFactory:

    @staticmethod
    async def create_dataset(voltage: str) -> XcomDataset:
        """
        The actual XcomDataset list is kept in a separate json file to reduce the memory size needed to load the integration.
        The list is only loaded during config flow and during initial startup, and then released again.
        """
        async with aiofiles_open(XcomDataset.PATH_120V, "r", encoding="UTF-8") as file_120vac:
            text_120vac = await file_120vac.read()
        async with aiofiles_open(XcomDataset.PATH_240V, "r", encoding="UTF-8") as file_240vac:
            text_240vac = await file_240vac.read()
        
        values_120vac = orjson.loads(text_120vac)
        values_240vac = orjson.loads(text_240vac)

        datapoints_120vac = list(filter(None, [XcomDatapoint.from_dict(val) for val in values_120vac]))
        datapoints_240vac = list(filter(None, [XcomDatapoint.from_dict(val) for val in values_240vac]))

        # start with the 240v list as base
        datapoints = datapoints_240vac

        if voltage == XcomVoltage.AC120:
            # Merge the 120v list into the 240v one by replacing duplicates. This maintains the order of menu items
            for dp120 in datapoints_120vac:
                # already in result?
                index = next( (idx for idx,dp240 in enumerate(datapoints) if dp120.nr == dp240.nr and dp120.family_id == dp240.family_id ), None)
                if index is not None:
                    datapoints[index] = dp120

            _LOGGER.info(f"Using {len(datapoints)} datapoints for 120 Vac")

        elif voltage == XcomVoltage.AC240:
            _LOGGER.info(f"Using {len(datapoints)} datapoints for 240 Vac")

        else:
            msg = f"Unknown voltage: '{voltage}'"
            raise Exception(msg)

        return XcomDataset(datapoints)


    @staticmethod
    async def create_messageset(language: str = "en") -> XcomMessageSet:
        """
        The actual XcomMessage list is kept in a separate json file.
        """
        match language:
            case "en": path = XcomMessageDef.PATH_EN # English
            case _:
                msg = f"Unknown language: '{language}'"
                raise Exception(msg)
        
        async with aiofiles_open(path, "r", encoding="UTF-8") as f:
            text = await f.read()
        
        values = orjson.loads(text)
        messages = list(filter(None, [XcomMessageDef.from_dict(val) for val in values]))

        return XcomMessageSet(messages)


    @staticmethod
    async def parse_package(f: BufferedReader, timeout:float=REQ_TIMEOUT, verbose=False) -> XcomPackage:
        # package sometimes starts with 0xff
        skipped = bytearray(b'')
        ts_end = datetime.now() + timedelta(seconds=timeout)

        while datetime.now() < ts_end:
            sb = await readBytes(f, 1)
            if sb == XcomPackage.start_byte:
                break

            skipped.extend(sb)

        if verbose and len(skipped) > 0:
            _LOGGER.debug(f"skip {len(skipped)} bytes until start-byte ({binascii.hexlify(skipped).decode('ascii')})")

        h_raw = await readBytes(f, XcomHeader.length)
        h_chk = await readBytes(f, 2)
        assert XcomPackage.checksum(h_raw) == h_chk
        header = XcomHeader.parseBytes(h_raw)

        f_raw = await readBytes(f, header.data_length)
        f_chk = await readBytes(f, 2)
        assert XcomPackage.checksum(f_raw) == f_chk
        frame = XcomFrame.parseBytes(f_raw)

        return XcomPackage(header, frame)


    @staticmethod
    async def parse_package_bytes(buf: bytes, timeout:float=REQ_TIMEOUT, verbose=False) -> XcomPackage:
        reader = AsyncReader(buf)
        return await AsyncXcomFactory.parse_package(reader, timeout, verbose)
    
