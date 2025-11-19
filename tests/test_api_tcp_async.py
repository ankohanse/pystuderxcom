import asyncio
import copy
from datetime import datetime
import pytest
import pytest_asyncio

from pystuderxcom import AsyncXcomApiTcp, XcomApiTcp, XcomApiTcpMode
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
        self.server = None
        self.client = None

    async def start_server(self, listen_port):
        if not self.server:
            self.server = AsyncXcomApiTcp(mode=XcomApiTcpMode.SERVER, listen_port=listen_port)

        await self.server.start(wait_for_connect = False)

    async def stop_server(self):
        if self.server:
            await self.server.stop()
        self.server = None

    async def start_client(self, remote_ip, remote_port):
        if not self.client:
            self.client = AsyncXcomApiTcp(mode=XcomApiTcpMode.CLIENT, remote_ip=remote_ip, remote_port=remote_port)

        await self.client.start()

    async def stop_client(self):
        if self.client:
            await self.client.stop()
        self.client = None


@pytest_asyncio.fixture
async def context():
    # Prepare
    ctx = TestContext()

    # pass objects to tests
    yield ctx

    # cleanup
    await ctx.stop_client()
    await ctx.stop_server()


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
@pytest.mark.usefixtures("context", "unused_tcp_port")
@pytest.mark.parametrize(
    "name, start_server, start_client, exp_server_conn, exp_client_conn, exp_server_ip, exp_client_ip",
    [
        ("connect ok",       True,  True,  True,  True,  "127.0.0.1", "127.0.0.1"),
        ("connect timeout",  True,  False, False, False, None, None),
        ("connect no start", False, False, False, False, None, None),
    ]
)
async def test_connect(name, start_server, start_client, exp_server_conn, exp_client_conn, exp_server_ip, exp_client_ip, request):

    context     = request.getfixturevalue("context")
    server_port = request.getfixturevalue("unused_tcp_port")
    server_ip   = "127.0.0.1"

    assert context.server is None
    assert context.client is None

    task_server = await AsyncTaskHelper(context.start_server, server_port).start() if start_server else None
    task_client = await AsyncTaskHelper(context.start_client, server_ip, server_port).start() if start_client else None

    if task_server is not None:
        await task_server.join()
        assert context.server is not None

    if task_client is not None:
        await task_client.join()
        assert context.client is not None
        assert context.client.connected == exp_client_conn

    assert context.server is None or context.server.connected == exp_server_conn
    assert context.server is None or context.server.remote_ip == exp_server_ip



@pytest.mark.asyncio
@pytest.mark.usefixtures("context", "unused_tcp_port", "package_read_info")
@pytest.mark.parametrize(
    "name, exp_data",
    [
        ("receive ok",      True),
        ("receive timeout", False),
    ]
)
async def test_send_receive(name, exp_data, request):
    context = request.getfixturevalue("context")
    package = request.getfixturevalue("package_read_info")
    server_port = request.getfixturevalue("unused_tcp_port")
    server_ip   = "127.0.0.1"

    task_server = await AsyncTaskHelper(context.start_server, server_port).start()
    task_client = await AsyncTaskHelper(context.start_client, server_ip, server_port).start()

    await task_server.join()
    await task_client.join()

    assert context.server.connected == True
    assert context.client.connected == True

    # Perform a receive from client to server
    if exp_data:
        task_client = await AsyncTaskHelper(context.client._sendPackage, package).start()
        task_server = await AsyncTaskHelper(context.server._receivePackage).start()
        
        rsp_package = await task_server.join()
        await task_client.join()

        assert rsp_package is not None
        assert rsp_package.header.src_addr == package.header.src_addr
        assert rsp_package.header.dst_addr == package.header.dst_addr
        assert rsp_package.frame_data.service_id == package.frame_data.service_id
        assert rsp_package.frame_data.service_data.object_type == package.frame_data.service_data.object_type
        assert rsp_package.frame_data.service_data.object_id == package.frame_data.service_data.object_id
        assert rsp_package.frame_data.service_data.property_id == package.frame_data.service_data.property_id

    else:
        task_server = await AsyncTaskHelper(context.server._receivePackage).start()
        rsp_package = await task_server.join()

        assert rsp_package is None
