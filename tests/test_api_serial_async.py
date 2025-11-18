import asyncio
import copy
from datetime import datetime
import pytest
import pytest_asyncio

from pystuderxcom import AsyncXcomApiSerial, XcomApiSerial
from pystuderxcom import AsyncXcomFactory, XcomFactory
from pystuderxcom import XcomApiTimeoutException, XcomApiResponseIsError, XcomParamException
from pystuderxcom import XcomDataset, XcomData, XcomPackage
from pystuderxcom import XcomValues, XcomValuesItem
from pystuderxcom import XcomVoltage, XcomFormat, XcomAggregationType, ScomService, ScomObjType, ScomObjId, ScomQspId, ScomAddress, ScomErrorCode
from pystuderxcom import XcomDataMessageRsp
from . import AsyncTaskHelper, TaskHelper


class TestContext:
    __test__ = False  # Prevent pytest from collecting this class

    def __init__(self):
        self.local = None
        self.remote = None

    async def start_local(self, port):
        if not self.local:
            self.local = AsyncXcomApiSerial(port)

        await self.local.start()

    async def stop_local(self):
        if self.local:
            await self.local.stop()
        self.local = None

    async def start_remote(self, port):
        if not self.remote:
            self.remote = AsyncXcomApiSerial(port)

        await self.remote.start()

    async def stop_remote(self):
        if self.remote:
            await self.remote.stop()
        self.remote = None


@pytest_asyncio.fixture(scope="function")
async def context():
    # Prepare
    ctx = TestContext()

    # pass objects to tests
    yield ctx

    # cleanup
    await ctx.stop_local()
    await ctx.stop_remote()

    # Give some time to really free up the COM ports
    await asyncio.sleep(1)


@pytest_asyncio.fixture
async def package_read_info():
    yield XcomPackage.genPackage(
        service_id = ScomService.READ,
        object_type = ScomObjType.INFO,
        object_id = 0x01020304,
        property_id = ScomQspId.VALUE,
        property_data = XcomData.NONE,
        src_addr = ScomAddress.SOURCE,
        dst_addr = 101,
    )


@pytest.mark.asyncio(scope="function")
@pytest.mark.usefixtures("context")
@pytest.mark.parametrize(
    "name, start_local, start_remote, local_port, remote_port, exp_local_conn, exp_remote_conn",
    [
        ("connect ok",       True,  True,  "COM2", "COM3", True,  True),
        ("connect timeout",  True,  False, "COM2", None,   True,  False),
        ("connect no start", False, False, None,   None,   False, False),
    ]
)
async def test_connect(name, start_local, start_remote, local_port, remote_port, exp_local_conn, exp_remote_conn, request):

    context = request.getfixturevalue("context")

    assert context.local is None
    assert context.remote is None

    task_local = await AsyncTaskHelper(context.start_local, local_port).start() if start_local else None
    task_remote = await AsyncTaskHelper(context.start_remote, remote_port).start() if start_remote else None

    if task_local is not None:
        await task_local.join()
        assert context.local is not None

    if task_remote is not None:
        await task_remote.join()
        assert context.remote is not None

    assert context.local is None or context.local.connected == exp_local_conn
    assert context.remote is None or context.remote.connected == exp_remote_conn


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "package_read_info")
@pytest.mark.parametrize(
    "name, exp_data",
    [
        ("receive ok",      True),
        ("receive timeout", False),
    ]
)
async def test_send_receive_package(name, exp_data, request):
    context = request.getfixturevalue("context")
    package = request.getfixturevalue("package_read_info")
    local_port   = "COM2"
    remote_port  = "COM3"

    task_local = await AsyncTaskHelper(context.start_local, local_port).start()
    task_remote = await AsyncTaskHelper(context.start_remote, remote_port).start()

    await task_local.join()
    assert context.local is not None
    assert context.local.connected == True

    await task_remote.join()
    assert context.remote is not None
    assert context.remote.connected == True

    # Perform a receive to local from remote
    if exp_data:
        task_remote = await AsyncTaskHelper(context.remote._sendPackage, package).start()
        task_local = await AsyncTaskHelper(context.local._receivePackage).start()
        
        rsp_package = await task_local.join()
        await task_remote.join()

        assert rsp_package is not None
        assert rsp_package.header.src_addr == package.header.src_addr
        assert rsp_package.header.dst_addr == package.header.dst_addr
        assert rsp_package.frame_data.service_id == package.frame_data.service_id
        assert rsp_package.frame_data.service_data.object_type == package.frame_data.service_data.object_type
        assert rsp_package.frame_data.service_data.object_id == package.frame_data.service_data.object_id
        assert rsp_package.frame_data.service_data.property_id == package.frame_data.service_data.property_id

    else:
        task_local = await AsyncTaskHelper(context.local._receivePackage).start()
        rsp_package = await task_local.join()

        assert rsp_package is None
