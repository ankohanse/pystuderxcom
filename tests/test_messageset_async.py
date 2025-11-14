import pytest
import pytest_asyncio
from pystuderxcom import XcomLevel
from pystuderxcom import XcomMessage, XcomMessageDef, XcomMessageSet, XcomMessageUnknownException
from pystuderxcom import AsyncXcomFactory


@pytest.mark.asyncio
async def test_create():
    msg_set = await AsyncXcomFactory.create_messageset()    

    assert len(msg_set._messages) == 189


@pytest.mark.asyncio
async def test_nr():
    msg_set = await AsyncXcomFactory.create_messageset()

    msg_def = msg_set.getByNr(0)
    assert msg_def.level == XcomLevel.VO
    assert msg_def.number == 0
    assert msg_def.string is not None

    msg_def = msg_set.getByNr(235)
    assert msg_def.level == XcomLevel.VO
    assert msg_def.number == 235
    assert msg_def.string is not None

    with pytest.raises(XcomMessageUnknownException):
        msg_def = msg_set.getByNr(236)

    with pytest.raises(XcomMessageUnknownException):
        msg_def = msg_set.getByNr(-1)


@pytest.mark.asyncio
async def test_str():
    msg_set = await AsyncXcomFactory.create_messageset()

    s = msg_set.getStringByNr(0)
    assert s is not None

    s = msg_set.getStringByNr(235)
    assert s is not None

    with pytest.raises(XcomMessageUnknownException):
        s = msg_set.getStringByNr(236)

    with pytest.raises(XcomMessageUnknownException):
        s = msg_set.getStringByNr(-1)
