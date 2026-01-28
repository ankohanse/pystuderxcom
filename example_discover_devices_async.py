import asyncio
from dataclasses import asdict
import logging
import sys

from pystuderxcom import AsyncXcomApiTcp, XcomApiTcp, XcomApiTcpMode
from pystuderxcom import AsyncXcomDiscover, XcomDiscover
from pystuderxcom import AsyncXcomFactory, XcomFactory
from pystuderxcom import XcomDataset, XcomVoltage
from helper import RunHelper

# Setup logging to StdOut
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    api = AsyncXcomApiTcp(mode=XcomApiTcpMode.SERVER, listen_port=4001)    # port number configured in Xcom-LAN/Moxa NPort
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240, XcomVoltage.DC48) # or use XcomVoltage.AC120, XcomVoltage.DC12 or XcomVoltagC.DC24 

    try:
        if not await api.start():
            logger.info(f"Did not connect to Xcom")
            return
        
        helper = AsyncXcomDiscover(api, dataset)

        # Discover Xcom client info
        client_info = await helper.discover_client_info()

        logger.info(f"\n\n")
        logger.info(f"Discovered {client_info}")

        # Discover Xcom devices
        devices = await helper.discover_devices(getExtendedInfo=True, verbose=False)

        logger.info(f"\n\n")
        for device in devices:
            logger.info(f"Discovered {device}")

        # Log diagnostic information
        diag = await api.get_diagnostics()
        logger.info(f"Diagnostics: {diag}")

    finally:
        await api.stop()
        dataset = None


RunHelper.run(main)  # main loop
