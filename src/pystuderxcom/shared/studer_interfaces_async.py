"""
Shared Interfaces 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

from enum import StrEnum

from .studer_types import (
    StuderDiscoveredDevice,
    StuderDiscoveredGateway,
)


class StuderDiscoverFlags(StrEnum):
    SKIP_GUID = "skip_guid"


class AsyncStuderDiscover:

    async def discover_devices(self, getExtendedInfo = False, verbose = False) -> list[StuderDiscoveredDevice]:
        """
        Discover which Studer devices can be reached
        """
        raise NotImplementedError("Function discover_devices must be implemented in derived class")


    async def get_extended_device_info(self, device: StuderDiscoveredDevice, verbose=False) -> StuderDiscoveredDevice:
        """
        Discover which Studer devices can be reached
        """
        raise NotImplementedError("Function get_extended_device_info must be implemented in derived class")
    

    async def discover_gateway_info(self, flags:dict={}, verbose=False) -> StuderDiscoveredGateway:
        """
        Discover extended info about the remote Xcom / Next Gateway we are connected to
        """
        raise NotImplementedError("Function discover_gateway_info must be implemented in derived class")


    @staticmethod
    async def discover_webconfig(hint: str = None) -> str:
        """
        Discover if Moxa / NextGateway Web Config page can be found on the local network
        """
        raise NotImplementedError("Function discover_webconfig must be implemented in derived class")    
