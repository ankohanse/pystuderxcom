"""
Shared Interfaces 

Note that this file is shared as is between pystuderxcom and pystudernext.
Do not place code that is specific to only one of these libraries in here!
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Iterable

from ..shared.studer_dataset import StuderDatapoint
from ..shared.studer_types import StuderDiscoveredDevice, StuderDiscoveredGateway
from ..shared.studer_valueset import StuderValueSet


###
### Studer API
### 

class AsyncStuderApi:

    async def start(self) -> bool:
        """
        Connect to the remote gateway
        """
        raise NotImplementedError("Function start() must be implemented in derived class")

    async def stop(self):
        """
        Close the client
        """
        raise NotImplementedError("Function stop() must be implemented in derived class")

    @property
    def connected(self) -> bool:
        """
        Indicate whether we are connected to the remote gateway
        """
        raise NotImplementedError("Property connected must be implemented in derived class")

    async def request_value(self, parameter: StuderDatapoint, device: StuderDiscoveredDevice|int|str=None, retries = None, timeout = None, verbose=False):
        """
        Request a datapoint for a device.
        Device can be a StuderDisconnectedDevice, a slave/address or a device code.
        Returns None if not connected, otherwise returns the requested value
        """
        raise NotImplementedError("Function request_value() must be implemented in derived class")

    async def request_values(self, request_data: StuderValueSet, retries = None, timeout = None, verbose=False) -> StuderValueSet:
        """
        Request multiple datapoints for devices in one call.
        Can only retrieve actual device values, NOT the average or sum over multiple devices.
        """
        raise NotImplementedError("Function request_value() must be implemented in derived class")

    async def update_value(self, parameter: StuderDatapoint, value: Any, device: StuderDiscoveredDevice|int|str=None, retries = None, timeout = None, verbose=False):
        """
        Update a datapoint for a device
        Returns None if not connected, otherwise returns True on success
        """
        raise NotImplementedError("Function request_value() must be implemented in derived class")

        
###
### Studer Discover
### 

class StuderDiscoverFlags(StrEnum):
    SKIP_GUID = "skip_guid"


class AsyncStuderDiscover:

    async def discover_devices(self, getExtendedInfo = False, verbose = False) -> list[StuderDiscoveredDevice]:
        """
        Discover which Studer devices can be reached
        """
        raise NotImplementedError("Function discover_devices(...) must be implemented in derived class")


    async def get_extended_device_info(self, device: StuderDiscoveredDevice, verbose=False) -> StuderDiscoveredDevice:
        """
        Discover which Studer devices can be reached
        """
        raise NotImplementedError("Function get_extended_device_info(...) must be implemented in derived class")
    

    async def discover_gateway_info(self, flags:dict={}, verbose=False) -> StuderDiscoveredGateway:
        """
        Discover extended info about the remote Xcom / Next Gateway we are connected to
        """
        raise NotImplementedError("Function discover_gateway_info(...) must be implemented in derived class")


    @staticmethod
    async def discover_webconfig(hint: str = None) -> str:
        """
        Discover if Moxa / NextGateway Web Config page can be found on the local network
        """
        raise NotImplementedError("Function discover_webconfig must be implemented in derived class")    
