import asyncio
import logging
import os
import socket
import threading

from ipaddress import IPv4Network, IPv4Address, IPv6Address, ip_address
from types import TracebackType
from typing import Optional, Type


_LOGGER = logging.getLogger(__name__)


class HybridLock:
    """A lock that can be used interchangeably with both 'with' and 'async with'."""
    
    def __init__(self) -> None:
        self._lock = threading.Lock()

    # --- Synchronous Context Manager Protocol ---
    def __enter__(self) -> "HybridLock":
        self._lock.acquire()
        return self

    def __exit__(
        self, 
        exc_type: Optional[Type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional[TracebackType]
    ) -> None:
        self._lock.release()

    # --- Asynchronous Context Manager Protocol ---
    async def __aenter__(self) -> "HybridLock":
        # Run the blocking acquire() inside an executor thread 
        # so it doesn't stall the async event loop.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._lock.acquire)
        return self

    async def __aexit__(
        self, 
        exc_type: Optional[Type[BaseException]], 
        exc_val: Optional[BaseException], 
        exc_tb: Optional[TracebackType]
    ) -> None:
        # Releasing a threading.Lock is instantaneous and non-blocking
        self._lock.release()


class StuderNetworkHelper:
    
    @staticmethod
    def get_my_ip():
        """
        Find my IP address
        :return:
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip


    @staticmethod
    def get_local_ips_via_arp() -> set[IPv4Address|IPv6Address]:
        """
        Find ip address candidates known in the local network.
        Will only return addresses that this computer had recently communicated with
        """
        ips: set[str] = set()
        for line in os.popen('arp -a'):     # arp seems to be available on Linux, Windows and Pi
            try:
                # Linux:  
                #   ? (192.168.88.250) at 00:90:e8:3c:f8:7e [ether] on end0
                #   ...
                # Windows: 
                #   Interface: 192.168.88.100 --- 0x4
                #     Internet Address      Physical Address      Type
                #     192.168.88.250        00-90-e8-3c-f8-7e     dynamic 
                #     ...
                
                device = line.strip('?').split()[0].strip('()')
                ips.add( ip_address(device) )
            except:
                pass

        return ips


    @staticmethod
    def get_local_ips_via_network():
        """
        Find ip address candidates known in the local network
        """
        ips: set[str] = set()

        local_ip = StuderNetworkHelper.get_my_ip()
        network = IPv4Network(f"{local_ip}/24", strict=False)
        for host in network.hosts():
            ips.add( host )

        return ips


def safe_isinstance(obj, cls) -> bool:
    """
    Safe version of isinstance that is aware of shared classes.
    I.e. safe_isinstance(obj, StuderDiscoveredDevice) will return True both
    on pystuderxcom.shared.StuderDiscoveredDevice as well as
    on pystudernext.shared.StuderDiscoveredDevice
    """
    if type(obj).__module__.startswith('pystuderxcom.shared.') or \
       type(obj).__module__.startswith('pystudernext.shared.') or \
       cls.__module__.startswith('pystuderxcom.shared.') or \
       cls.__module__.startswith('pystudernext.shared.'):

        # Make sure to compare on __mro__ so that parent classes are also matched
        result = any(t.__name__ == cls.__name__ for t in type(obj).__mro__)
        return result
    else:
        return isinstance(obj, cls)

