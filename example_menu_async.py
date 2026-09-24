import asyncio
import logging
import sys

from pystuderxcom import StuderDataType
from pystuderxcom import XcomVoltage
from pystuderxcom import XcomDeviceFamilies
from pystuderxcom import XcomDataset
from helper import RunHelper

# Setup logging to StdOut
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Print entire menu structure
    families = await XcomDeviceFamilies.async_get_instance()
    dataset = await XcomDataset.async_get_instance(XcomVoltage.AC240, XcomVoltage.DC48) # or use XcomVoltage.AC120, XcomVoltage.DC12 or XcomVoltage.DC24 

    # Helper function to recursively print the entire menu
    async def print_menu(family, parent_id, indent="    "):
        items = dataset.get_menu_items(family, parent_id)
        for item in items:
            if item.data_type == StuderDataType.MENU:
                logger.info(f"{indent}{item.label}")

                await print_menu(family, str(item.id), indent+"  ")
            else:
                logger.info(f"{indent}{item.label} ({item.address})")

    for family in families:
        logger.info(f"")
        logger.info(f"{family.model}")
        await print_menu(family, "", "  ")

    dataset = None  # Release memory of the dataset


RunHelper.run(main)  # main loop