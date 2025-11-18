import asyncio
from dataclasses import asdict
import logging
import sys

from pystuderxcom import AsyncXcomApiTcp, XcomApiTcp
from pystuderxcom import AsyncXcomDiscover, XcomDiscover
from pystuderxcom import AsyncXcomFactory, XcomFactory
from pystuderxcom import XcomDataset, XcomVoltage

# Setup logging to StdOut
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Discover all Xcom devices
    api     = AsyncXcomApiTcp(4001)    # port number configured in Xcom-LAN/Moxa NPort
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240) # or use XcomVoltage.AC120

    try:
        if not await api.start():
            logger.info(f"Did not connect to Xcom")
            return
        
        helper = AsyncXcomDiscover(api, dataset)

        # Discover Xcom client info
        client_info = await helper.discoverClientInfo()

        logger.info(f"\n\n")
        logger.info(f"Discovered {client_info}")

        # Discover Xcom devices
        devices = await helper.discoverDevices(getExtendedInfo=True, verbose=False)

        logger.info(f"\n\n")
        for device in devices:
            logger.info(f"Discovered {device}")

        # Log diagnostic information
        diag = await api.getDiagnostics()
        logger.info(f"Diagnostics: {diag}")

    finally:
        await api.stop()
        dataset = None


asyncio.run(main())  # main loop
