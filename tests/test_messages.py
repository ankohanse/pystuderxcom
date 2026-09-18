import pytest
import pytest_asyncio
from pystuderxcom import StuderUserLevel
from pystuderxcom import XcomMessage, XcomMessageDef, XcomMessageSet
from pystuderxcom import StuderMessageUnknownException


def test_init():
    XcomMessageSet.del_instance()
    with pytest.raises(RuntimeError):
        dataset = XcomMessageSet() 


@pytest.mark.asyncio
async def test_get_instance_async():
    XcomMessageSet.del_instance()
    msg_set = await XcomMessageSet.async_get_instance()

    assert len(msg_set._messages) == 189


def test_get_instance_sync():
    XcomMessageSet.del_instance()
    msg_set = XcomMessageSet.get_instance()

    assert len(msg_set._messages) == 189


def test_nr():
    XcomMessageSet.del_instance()
    msg_set = XcomMessageSet.get_instance()

    msg_def = msg_set.get_by_nr(0)
    assert msg_def.level == StuderUserLevel.VIEWONLY
    assert msg_def.number == 0
    assert msg_def.string is not None

    msg_def = msg_set.get_by_nr(235)
    assert msg_def.level == StuderUserLevel.VIEWONLY
    assert msg_def.number == 235
    assert msg_def.string is not None

    with pytest.raises(StuderMessageUnknownException):
        msg_def = msg_set.get_by_nr(236)

    with pytest.raises(StuderMessageUnknownException):
        msg_def = msg_set.get_by_nr(-1)


def test_str():
    XcomMessageSet.del_instance()
    msg_set = XcomMessageSet.get_instance()

    s = msg_set.str_by_nr(0)
    assert s is not None

    s = msg_set.str_by_nr(235)
    assert s is not None

    with pytest.raises(StuderMessageUnknownException):
        s = msg_set.str_by_nr(236)

    with pytest.raises(StuderMessageUnknownException):
        s = msg_set.str_by_nr(-1)
