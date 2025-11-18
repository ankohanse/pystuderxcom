import asyncio
import copy
import threading
import pytest
import pytest_asyncio

from pystuderxcom import AsyncXcomDiscover, XcomDiscover
from pystuderxcom import AsyncXcomFactory, XcomFactory
from pystuderxcom import XcomDataset, XcomData, XcomPackage
from pystuderxcom import XcomApiTimeoutException, XcomApiResponseIsError
from pystuderxcom import XcomVoltage, XcomFormat, ScomService, ScomObjType, ScomQspId, ScomErrorCode
from . import AsyncTestApi, TestApi


async def on_receive(api: AsyncTestApi):
    """Helper to turn a request into a response"""
    req: XcomPackage = api.request_package
    if req:
        if req.header.dst_addr not in api.rsp_dest:
            flags = 0x03
            data = XcomData.pack(ScomErrorCode.DEVICE_NOT_FOUND, XcomFormat.ERROR)

        elif str(req.frame_data.service_data.object_id) not in api.rsp_dict:
            flags = 0x03
            data = XcomData.pack(ScomErrorCode.READ_PROPERTY_FAILED, XcomFormat.ERROR)

        else:
            flags = 0x02
            data = api.rsp_dict[str(req.frame_data.service_data.object_id)]

        api.response_package = copy.deepcopy(api.request_package)
        api.response_package.frame_data.service_flags = flags
        api.response_package.frame_data.service_data.property_data = data
        api.response_package.header.data_length = len(api.response_package.frame_data)


class TestContext():

    def __init__(self):
        self.dataset = None
        self.api = None
        self.discover = None

    async def start_discover(self, rsp_dest, rsp_dict):
        self.dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240)
        self.api = AsyncTestApi(on_receive_handler=on_receive, rsp_dest=rsp_dest, rsp_dict=rsp_dict)
    
        self.discover = AsyncXcomDiscover(self.api, self.dataset)    

    async def stop_discover(self):
        self.api = None
        self.dataset = None
        self.discover = None


@pytest_asyncio.fixture
async def context():
    # Prepare
    ctx = TestContext()

    # pass objects to tests
    yield ctx

    # cleanup
    await ctx.stop_discover()


@pytest.mark.asyncio
@pytest.mark.usefixtures("context")
@pytest.mark.parametrize(
    "name, rsp_dest, rsp_dict, exp_devices",
    [
        ("none",        [],             { "3000": XcomData.pack(1234.0, XcomFormat.FLOAT) },  []),
        ("xt1",         [101],          { "3000": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["XT1"]),
        ("xt1,xt2,xt3", [101,102,103],  { "3000": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["XT1", "XT2", "XT3"]),
        ("l1",          [191],          { "3000": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["L1"]),
        ("l1,l2,l3",    [191,192,193],  { "3000": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["L1", "L2", "L3"]),
        ("rcc",         [501],          { "5002": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["RCC"]),
        ("bsp",         [601],          { "7034": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["BSP"]),
        ("bms",         [601],          { "7054": XcomData.pack(1234.0, XcomFormat.FLOAT) },  ["BMS"]),
        ("vt1",         [301],          { "11000": XcomData.pack(1234.0, XcomFormat.FLOAT) }, ["VT1"]),
        ("vt1,vt2",     [301,302],      { "11000": XcomData.pack(1234.0, XcomFormat.FLOAT) }, ["VT1", "VT2"]),
        ("vs1",         [701],          { "15000": XcomData.pack(1234.0, XcomFormat.FLOAT) }, ["VS1"]),
        ("vs1,vs2",     [701,702],      { "15000": XcomData.pack(1234.0, XcomFormat.FLOAT) }, ["VS1", "VS2"]),
    ]
)
async def test_discover_devices(name, rsp_dest, rsp_dict, exp_devices, request):
    # Create discover instance
    context = request.getfixturevalue("context")
    await context.start_discover(rsp_dest, rsp_dict)

    # Perform the discover
    devices = await context.discover.discoverDevices(getExtendedInfo=False)

    # Check discovered devices
    assert len(devices) == len(exp_devices)
    for device in devices:
        assert device.code in exp_devices
        assert device.addr in rsp_dest
        assert device.family_id is not None
        assert device.family_model is not None
        
        assert device.device_model is None
        assert device.fid is None
        assert device.hw_version is None
        assert device.sw_version is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_tcp_port")
@pytest.mark.parametrize(
    "name, rsp_dest, rsp_dict, exp_code, exp_model, exp_hw_version, exp_sw_version, exp_fid",
    [
        ("xt1 none",    [101], {
                            "3000": XcomData.pack(1234.0, XcomFormat.FLOAT)  # detect
                        }, "XT1", None, None, None, None),
        ("xt1 ext",     [101], {
                            "3000": XcomData.pack(1234.0, XcomFormat.FLOAT), # detect
                            "3124": XcomData.pack(0x01, XcomFormat.FLOAT),   # device_model
                            "3129": XcomData.pack(0x0203, XcomFormat.FLOAT), # hw_version
                            "3132": XcomData.pack(0x0405, XcomFormat.FLOAT), # hw_version
                            "3130": XcomData.pack(0x0607, XcomFormat.FLOAT), # sw_version
                            "3131": XcomData.pack(0x0809, XcomFormat.FLOAT), # sw_version
                            "3156": XcomData.pack(0x0908, XcomFormat.FLOAT), # fid
                            "3157": XcomData.pack(0x0706, XcomFormat.FLOAT), # fid
                        }, "XT1", "XTH", "2.3 / 4.5", "6.8.9", "09080706"),
        ("bsp ext",     [601], {
                            "7034": XcomData.pack(1.0, XcomFormat.FLOAT),    # detect
                            "7034": XcomData.pack(10241, XcomFormat.FLOAT),  # device_model
                            "7036": XcomData.pack(0X0102, XcomFormat.FLOAT), # hw_version
                            "7037": XcomData.pack(0X0304, XcomFormat.FLOAT), # sw_version      
                            "7038": XcomData.pack(0X0506, XcomFormat.FLOAT), # sw_version
                            "7048": XcomData.pack(0x0708, XcomFormat.FLOAT), # fid
                            "7049": XcomData.pack(0x0901, XcomFormat.FLOAT), # fid
                        }, "BSP", None, "1.2", "3.5.6", "07080901"),
        ("bms ext",     [601], {
                            "7054": XcomData.pack(1.0, XcomFormat.FLOAT),    # detect
                            "7034": XcomData.pack(10241, XcomFormat.FLOAT),  # device_model
                            "7036": XcomData.pack(0X0102, XcomFormat.FLOAT), # hw_version
                            "7037": XcomData.pack(0X0304, XcomFormat.FLOAT), # sw_version   
                            "7038": XcomData.pack(0X0506, XcomFormat.FLOAT), # sw_version
                            "7048": XcomData.pack(0x0708, XcomFormat.FLOAT), # fid
                            "7049": XcomData.pack(0x0901, XcomFormat.FLOAT), # fid
                        }, "BMS", None, "1.2", "3.5.6", "07080901"),
        ("vt1 ext",     [301], {
                            "11000": XcomData.pack(1234.0, XcomFormat.FLOAT), #detect
                            "11047": XcomData.pack(9079, XcomFormat.FLOAT),   # device_model
                            "11049": XcomData.pack(0X0102, XcomFormat.FLOAT), # hw_version
                            "11050": XcomData.pack(0X0304, XcomFormat.FLOAT), # sw_version
                            "11051": XcomData.pack(0X0506, XcomFormat.FLOAT), # sw_version
                            "11067": XcomData.pack(0x0708, XcomFormat.FLOAT), # fid
                            "11068": XcomData.pack(0x0901, XcomFormat.FLOAT), # fid
                        }, "VT1", None, "1.2", "3.5.6", "07080901"),
        ("vs1 ext",     [701], {
                            "15000": XcomData.pack(1234.0, XcomFormat.FLOAT), # detect
                            "15074": XcomData.pack(12801, XcomFormat.FLOAT),  # device_model
                            "15076": XcomData.pack(0X0102, XcomFormat.FLOAT), # hw_version
                            "15077": XcomData.pack(0X0304, XcomFormat.FLOAT), # sw_version
                            "15078": XcomData.pack(0X0506, XcomFormat.FLOAT), # sw_version
                            "15102": XcomData.pack(0x0708, XcomFormat.FLOAT), # fid 
                            "15103": XcomData.pack(0x0901, XcomFormat.FLOAT), # fid  
                        }, "VS1", "VS120", "1.2", "3.5.6", "07080901"),
    ]
)
async def test_discover_extendedinfo(name, rsp_dest, rsp_dict, exp_code, exp_model, exp_hw_version, exp_sw_version, exp_fid, request):
    # Create discover instance
    context = request.getfixturevalue("context")
    await context.start_discover(rsp_dest, rsp_dict)

    # Perform the discover
    devices = await context.discover.discoverDevices(getExtendedInfo=True)

    # Check discovered devices
    assert len(devices) == 1
    device = devices[0]

    assert device.code in exp_code
    assert device.device_model == exp_model
    assert device.hw_version == exp_hw_version
    assert device.sw_version == exp_sw_version
    assert device.fid == exp_fid


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_tcp_port")
@pytest.mark.parametrize(
    "name, rsp_dest, rsp_dict, exp_ip, exp_guid",
    [
        ("guid none",   [501], {
                            "5002": XcomData.pack("137aef81-08b7-4e70-ad89-0dad0563d627", XcomFormat.GUID),    
                    }, "127.0.0.1", None),
        ("guid ok",     [501], {
                            "0": XcomData.pack("137aef81-08b7-4e70-ad89-0dad0563d627", XcomFormat.GUID),    
                    }, "127.0.0.1", "137aef81-08b7-4e70-ad89-0dad0563d627"),
    ]        
)
async def test_clientinfo(name, rsp_dest, rsp_dict, exp_ip, exp_guid, request):
    # Create discover instance
    context = request.getfixturevalue("context")
    await context.start_discover(rsp_dest, rsp_dict)

    # Perform the discover
    client_info = await context.discover.discoverClientInfo()

    # Check discovered info
    assert client_info is not None
    assert client_info.ip == exp_ip
    assert client_info.guid == exp_guid
