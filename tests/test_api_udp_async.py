import asyncio
import copy
from datetime import datetime
import pytest
import pytest_asyncio

from pystuderxcom import AsyncXcomApiUdp, XcomApiUdp
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

    async def start_local(self, remote_ip, remote_port, local_port):
        if not self.local:
            self.local = AsyncXcomApiUdp(remote_ip, remote_port, local_port)

        await self.local.start()

    async def stop_local(self):
        if self.local:
            await self.local.stop()
        self.local = None

    async def start_remote(self, remote_ip, remote_port, local_port):
        if not self.remote:
            self.remote = AsyncXcomApiUdp(remote_ip, remote_port, local_port)

        await self.remote.start()

    async def stop_remote(self):
        if self.remote:
            await self.remote.stop()
        self.remote = None


@pytest_asyncio.fixture
async def context():
    # Prepare
    ctx = TestContext()

    # pass objects to tests
    yield ctx

    # cleanup
    await ctx.stop_local()
    await ctx.stop_remote()


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


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_udp_port_factory")
@pytest.mark.parametrize(
    "name, start_local, start_remote, exp_local_conn, exp_remote_conn, exp_local_ip, exp_remote_ip",
    [
        ("connect no start", False, False, False, False, None, None),
        ("connect timeout",  True,  False, True,  False, None, "127.0.0.1"),
        ("connect ok",       True,  True,  True,  True,  "127.0.0.1", "127.0.0.1"),
    ]
)
async def test_connect(name, start_local, start_remote, exp_local_conn, exp_remote_conn, exp_local_ip, exp_remote_ip, request):

    context = request.getfixturevalue("context")
    port_factory = request.getfixturevalue("unused_udp_port_factory")
    local_port   = port_factory()
    remote_port  = port_factory()

    assert context.local is None
    assert context.remote is None

    task_local = await AsyncTaskHelper(context.start_local, "127.0.0.1", remote_port, local_port).start() if start_local else None
    task_remote = await AsyncTaskHelper(context.start_remote, "127.0.0.1", local_port, remote_port).start() if start_remote else None

    if task_local is not None:
        await task_local.join()
        assert context.local is not None

    if task_remote is not None:
        await task_remote.join()
        assert context.remote is not None

    assert context.local is None or context.local.connected == exp_local_conn
    assert context.remote is None or context.remote.connected == exp_remote_conn

    assert context.local is None or context.local.remote_ip == exp_remote_ip


@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_udp_port_factory", "package_read_info")
@pytest.mark.parametrize(
    "name, exp_data",
    [
        ("receive ok",      True),
        ("receive timeout", False),
    ]
)
async def test_send_receive_package(name, exp_data, request):
    context = request.getfixturevalue("context")
    port_factory = request.getfixturevalue("unused_udp_port_factory")
    local_port   = port_factory()
    remote_port  = port_factory()
    package = request.getfixturevalue("package_read_info")

    task_local = await AsyncTaskHelper(context.start_local, "127.0.0.1", remote_port, local_port).start()
    task_remote = await AsyncTaskHelper(context.start_remote, "127.0.0.1", local_port, remote_port).start()

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
