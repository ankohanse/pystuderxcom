import asyncio
import copy
import threading
import pytest
import pytest_asyncio

from pystuderxcom import AsyncXcomDiscover, XcomDiscover, StuderDiscoverFlags
from pystuderxcom import XcomDataset, XcomData, XcomPackage, XcomVoltage
from pystuderxcom import XcomApiTimeoutException, XcomApiResponseIsError
from pystuderxcom import ScomServiceId, ScomObjType, ScomQspId, ScomErrorCode
from pystuderxcom import StuderDataType
from . import AsyncTestApi, TestApi


async def on_receive(api: AsyncTestApi):
    """Helper to turn a request into a response"""
    req: XcomPackage = api.request_package
    if req:
        if req.header.dst_addr not in api.rsp_dest:
            flags = 0x03
            data = XcomData.pack(ScomErrorCode.DEVICE_NOT_FOUND, StuderDataType.ERROR)

        elif str(req.frame_data.service_data.object_id) not in api.rsp_dict:
            flags = 0x03
            data = XcomData.pack(ScomErrorCode.READ_PROPERTY_FAILED, StuderDataType.ERROR)

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
        self.dataset = await XcomDataset.async_get_instance(XcomVoltage.AC240, XcomVoltage.DC48)
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
        ("none",        [990],              { "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["XCOM"]),
        ("xt1",         [101,990],          { "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["XT1", "XCOM"]),
        ("xt1,xt2,xt3", [101,102,103,990],  { "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["XT1", "XT2", "XT3", "XCOM"]),
        ("l1",          [191,990],          { "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["L1", "XCOM"]),
        ("l1,l2,l3",    [191,192,193,990],  { "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["L1", "L2", "L3", "XCOM"]),
        ("rcc",         [501,990],          { "5002": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["RCC", "XCOM"]),
        ("bsp",         [601,990],          { "7034": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["BSP", "XCOM"]),
        ("bms",         [601,990],          { "7054": XcomData.pack(1234.0, StuderDataType.FLOAT32) },  ["BMS", "XCOM"]),
        ("vt1",         [301,990],          { "11000": XcomData.pack(1234.0, StuderDataType.FLOAT32) }, ["VT1", "XCOM"]),
        ("vt1,vt2",     [301,302,990],      { "11000": XcomData.pack(1234.0, StuderDataType.FLOAT32) }, ["VT1", "VT2", "XCOM"]),
        ("vs1",         [701,990],          { "15000": XcomData.pack(1234.0, StuderDataType.FLOAT32) }, ["VS1", "XCOM"]),
        ("vs1,vs2",     [701,702,990],      { "15000": XcomData.pack(1234.0, StuderDataType.FLOAT32) }, ["VS1", "VS2", "XCOM"]),
    ]
)
async def test_discover_devices(name, rsp_dest, rsp_dict, exp_devices, request):
    # Create discover instance
    context = request.getfixturevalue("context")
    await context.start_discover(rsp_dest, rsp_dict)

    # Perform the discover
    devices = await context.discover.discover_devices(getExtendedInfo=False)

    # Check discovered devices
    assert len(devices) == len(exp_devices)
    for device in devices:
        assert device.code in exp_devices
        assert device.address in rsp_dest
        assert device.family_id is not None
        assert device.family_model is not None
        
        assert device.device_model is None
        assert device.serial is None
        assert device.hw_version is None
        assert device.sw_version is None
        assert device.om_version is None


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_tcp_port")
@pytest.mark.parametrize(
    "name, rsp_dest, rsp_dict, exp_code, exp_model, exp_hw_version, exp_sw_version, exp_serial",
    [
        ("xt1 none",    [101], {
                            "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32)  # detect
                        }, "XT1", None, None, None, None),
        ("xt1 ext",     [101], {
                            "3000": XcomData.pack(1234.0, StuderDataType.FLOAT32), # detect
                            "3124": XcomData.pack(0x01, StuderDataType.FLOAT32),   # device_model
                            "3129": XcomData.pack(0x0203, StuderDataType.FLOAT32), # hw_version
                            "3132": XcomData.pack(0x0405, StuderDataType.FLOAT32), # hw_version
                            "3130": XcomData.pack(0x0607, StuderDataType.FLOAT32), # sw_version
                            "3131": XcomData.pack(0x0809, StuderDataType.FLOAT32), # sw_version
                            "3156": XcomData.pack(0x0908, StuderDataType.FLOAT32), # fid
                            "3157": XcomData.pack(0x0706, StuderDataType.FLOAT32), # fid
                        }, "XT1", "XTH", "2.3 / 4.5", "6.8.9", "09080706"),
        ("bsp ext",     [601], {
                            "7034": XcomData.pack(1.0, StuderDataType.FLOAT32),    # detect
                            "7034": XcomData.pack(10241, StuderDataType.FLOAT32),  # device_model
                            "7036": XcomData.pack(0X0102, StuderDataType.FLOAT32), # hw_version
                            "7037": XcomData.pack(0X0304, StuderDataType.FLOAT32), # sw_version      
                            "7038": XcomData.pack(0X0506, StuderDataType.FLOAT32), # sw_version
                            "7048": XcomData.pack(0x0708, StuderDataType.FLOAT32), # fid
                            "7049": XcomData.pack(0x0901, StuderDataType.FLOAT32), # fid
                        }, "BSP", None, "1.2", "3.5.6", "07080901"),
        ("bms ext",     [601], {
                            "7054": XcomData.pack(1.0, StuderDataType.FLOAT32),    # detect
                            "7034": XcomData.pack(10241, StuderDataType.FLOAT32),  # device_model
                            "7036": XcomData.pack(0X0102, StuderDataType.FLOAT32), # hw_version
                            "7037": XcomData.pack(0X0304, StuderDataType.FLOAT32), # sw_version   
                            "7038": XcomData.pack(0X0506, StuderDataType.FLOAT32), # sw_version
                            "7048": XcomData.pack(0x0708, StuderDataType.FLOAT32), # fid
                            "7049": XcomData.pack(0x0901, StuderDataType.FLOAT32), # fid
                        }, "BMS", None, "1.2", "3.5.6", "07080901"),
        ("vt1 ext",     [301], {
                            "11000": XcomData.pack(1234.0, StuderDataType.FLOAT32), #detect
                            "11047": XcomData.pack(9079, StuderDataType.FLOAT32),   # device_model
                            "11049": XcomData.pack(0X0102, StuderDataType.FLOAT32), # hw_version
                            "11050": XcomData.pack(0X0304, StuderDataType.FLOAT32), # sw_version
                            "11051": XcomData.pack(0X0506, StuderDataType.FLOAT32), # sw_version
                            "11067": XcomData.pack(0x0708, StuderDataType.FLOAT32), # fid
                            "11068": XcomData.pack(0x0901, StuderDataType.FLOAT32), # fid
                        }, "VT1", None, "1.2", "3.5.6", "07080901"),
        ("vs1 ext",     [701], {
                            "15000": XcomData.pack(1234.0, StuderDataType.FLOAT32), # detect
                            "15074": XcomData.pack(12801, StuderDataType.FLOAT32),  # device_model
                            "15076": XcomData.pack(0X0102, StuderDataType.FLOAT32), # hw_version
                            "15077": XcomData.pack(0X0304, StuderDataType.FLOAT32), # sw_version
                            "15078": XcomData.pack(0X0506, StuderDataType.FLOAT32), # sw_version
                            "15102": XcomData.pack(0x0708, StuderDataType.FLOAT32), # fid 
                            "15103": XcomData.pack(0x0901, StuderDataType.FLOAT32), # fid  
                        }, "VS1", "VS120", "1.2", "3.5.6", "07080901"),
    ]
)
async def test_discover_extendedinfo(name, rsp_dest, rsp_dict, exp_code, exp_model, exp_hw_version, exp_sw_version, exp_serial, request):
    # Create discover instance
    context = request.getfixturevalue("context")
    await context.start_discover(rsp_dest, rsp_dict)

    # Perform the discover
    devices = await context.discover.discover_devices(getExtendedInfo=True)

    # Check discovered devices
    assert len(devices) == 2    # The target device plus the virtual Xcom device
    device = devices[0]

    assert device.code in exp_code
    assert device.device_model == exp_model
    assert device.hw_version == exp_hw_version
    assert device.sw_version == exp_sw_version
    assert device.serial == exp_serial


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_tcp_port")
@pytest.mark.parametrize(
    "name, flag_skip_guid, rsp_dest, rsp_dict, exp_host, exp_guid",
    [
        ("guid none",   False, [501], {
                            "5002": XcomData.pack("137aef81-08b7-4e70-ad89-0dad0563d627", StuderDataType.GUID),    
                    }, "127.0.0.1", None),
        ("guid ok",     False, [501], {
                            "0": XcomData.pack("137aef81-08b7-4e70-ad89-0dad0563d627", StuderDataType.GUID),    
                    }, "127.0.0.1", "137aef81-08b7-4e70-ad89-0dad0563d627"),
        ("guid skip",   True,  [501], {
                            "0": XcomData.pack("137aef81-08b7-4e70-ad89-0dad0563d627", StuderDataType.GUID),    
                    }, "127.0.0.1", None),
    ]        
)
async def test_discover_gateway_info(name, flag_skip_guid, rsp_dest, rsp_dict, exp_host, exp_guid, request):
    # Create discover instance
    context = request.getfixturevalue("context")
    await context.start_discover(rsp_dest, rsp_dict)

    # Perform the discover
    flags = {
        StuderDiscoverFlags.SKIP_GUID: flag_skip_guid,
    }
    gw_info = await context.discover.discover_gateway_info(flags)

    # Check discovered info
    assert gw_info is not None
    assert gw_info.host == exp_host
    assert gw_info.guid == exp_guid
