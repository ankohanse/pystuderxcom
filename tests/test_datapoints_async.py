import pytest
import pytest_asyncio

from pystuderxcom import (
    XcomDataset, 
    XcomVoltage, 
    XcomFormat, 
    XcomCategory, 
    XcomDatapointUnknownException,
    AsyncXcomFactory,
    XcomFactory,
)


@pytest.mark.asyncio
async def test_create():
    dataset120 = await AsyncXcomFactory.create_dataset(XcomVoltage.AC120)    
    dataset240 = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240)

    assert len(dataset120._datapoints) == 1451
    assert len(dataset240._datapoints) == 1451


@pytest.mark.asyncio
async def test_nr():
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240)

    param = dataset.get_by_nr(1107)
    assert param.family_id == "xt"
    assert param.nr == 1107
    assert param.format == XcomFormat.FLOAT
    assert param.category == XcomCategory.PARAMETER

    param = dataset.get_by_nr(1552)
    assert param.family_id == "xt"
    assert param.nr == 1552
    assert param.format == XcomFormat.LONG_ENUM
    assert param.category == XcomCategory.PARAMETER
    assert param.options != None
    assert type(param.options) is dict
    assert len(param.options) == 3

    param = dataset.get_by_nr(3000)
    assert param.family_id == "xt"
    assert param.nr == 3000
    assert param.format == XcomFormat.FLOAT
    assert param.category == XcomCategory.INFO

    param = dataset.get_by_nr(3000, "xt")
    assert param.family_id == "xt"
    assert param.nr == 3000
    assert param.format == XcomFormat.FLOAT
    assert param.category == XcomCategory.INFO

    param = dataset.get_by_nr(5012, "rcc")
    assert param.family_id == "rcc"
    assert param.nr == 5012
    assert param.format == XcomFormat.LONG_ENUM
    assert param.category == XcomCategory.PARAMETER
    assert param.options != None
    assert type(param.options) is dict

    with pytest.raises(XcomDatapointUnknownException):
        param = dataset.get_by_nr(9999)

    with pytest.raises(XcomDatapointUnknownException):
        param = dataset.get_by_nr(3000, "bsp")


@pytest.mark.asyncio
async def test_enum():
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240)

    param = dataset.get_by_nr(1552)
    assert param.options != None
    assert type(param.options) is dict
    assert len(param.options) == 3

    assert param.enum_value(1) == "Slow"
    assert param.enum_value("1") == "Slow"
    assert param.enum_value(0) == "0"
    assert param.enum_value("0") == "0"

    assert param.enum_key("Slow") == 1
    assert param.enum_key("Unknown") == None
    assert param.enum_key(1) == None
    assert param.enum_key("1") == None


@pytest.mark.asyncio
async def test_menu():
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240)
    
    root_items = dataset.get_menu_items(0)
    assert len(root_items) == 12

    for item in root_items:
        sub_items = dataset.get_menu_items(item.nr)
        assert len(sub_items) > 0

