import asyncio
import logging
import sys

from pystuderxcom import AsyncXcomFactory
from pystuderxcom import XcomFactory
from pystuderxcom import XcomVoltage, XcomFormat
from helper import RunHelper

# Setup logging to StdOut
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Print entire menu structure
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240) # or use XcomVoltage.AC120

    # Helper function to recursively print the entire menu
    async def print_menu(parent, indent=""):
        items = dataset.get_menu_items(parent)
        for item in items:
            logger.info(f"{indent}{item.nr}: {item.name}")

            if item.format == XcomFormat.MENU:
                await print_menu(item.nr, indent+"  ")

    await print_menu(0)
    dataset = None  # Release memory of the dataset


RunHelper.run(main)  # main loop