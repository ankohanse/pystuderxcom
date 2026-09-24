import pytest
import pytest_asyncio

from pystuderxcom import (
    StuderDatapointUnknownException,
    StuderDataset, 
    StuderDatapoint,
    StuderDataType,
    StuderParamException,
    StuderUserLevel,
    StuderAccess,
    StuderTarget,
    XcomVoltage, 
    XcomDataset,
    XcomDeviceFamilies,
)


def test_init():
    XcomDataset.del_instance()
    with pytest.raises(RuntimeError):
        dataset = XcomDataset() 


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "voltageAC, voltageDC, exp_len",
    [
        (XcomVoltage.AC120, XcomVoltage.DC12, 1461),
        (XcomVoltage.AC120, XcomVoltage.DC24, 1461),
        (XcomVoltage.AC120, XcomVoltage.DC48, 1461),
        (XcomVoltage.AC240, XcomVoltage.DC12, 1461),
        (XcomVoltage.AC240, XcomVoltage.DC24, 1461),
        (XcomVoltage.AC240, XcomVoltage.DC48, 1461),
    ]
)
async def test_async_get_instance(voltageAC, voltageDC, exp_len):
    XcomDataset.del_instance()
    dataset = await XcomDataset.async_get_instance(voltageAC, voltageDC)    

    assert len(dataset._datapoints) == exp_len

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "voltageAC, voltageDC, exp_len",
    [
        (XcomVoltage.AC120, XcomVoltage.DC12, 1461),
        (XcomVoltage.AC120, XcomVoltage.DC24, 1461),
        (XcomVoltage.AC120, XcomVoltage.DC48, 1461),
        (XcomVoltage.AC240, XcomVoltage.DC12, 1461),
        (XcomVoltage.AC240, XcomVoltage.DC24, 1461),
        (XcomVoltage.AC240, XcomVoltage.DC48, 1461),
    ]
)
def test_get_instance_sync(voltageAC, voltageDC, exp_len):
    XcomDataset.del_instance()
    dataset = XcomDataset.get_instance(voltageAC, voltageDC)    

    assert len(dataset._datapoints) == exp_len


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nr, family, exp_nr, exp_family_id, exp_data_type, exp_access, exp_target, exp_except",
    [
        (3000,  XcomDeviceFamilies.XTENDER, 3000, "xt", StuderDataType.FLOAT32, StuderAccess.READ, StuderTarget.STANDARD, None),
        (3000,  XcomDeviceFamilies.L1,      3000, "xt", StuderDataType.FLOAT32, StuderAccess.READ, StuderTarget.STANDARD, None), # L1, L2 and L3 use the datapoints from xt
        (3000,  "xt",  3000,  "xt",   StuderDataType.FLOAT32, StuderAccess.READ,       StuderTarget.STANDARD, None),
        (3000,  "l1",  3000,  "xt",   StuderDataType.FLOAT32, StuderAccess.READ,       StuderTarget.STANDARD, None), # L1, L2 and L3 use the datapoints from xt
        (3000,  None,  3000,  "xt",   StuderDataType.FLOAT32, StuderAccess.READ,       StuderTarget.STANDARD, None),
        (5012,  "rcc", 5012,  "rcc",  StuderDataType.ENUM32,  StuderAccess.READ_WRITE, StuderTarget.STANDARD, None),
        (99000, None,  99000, "xcom", StuderDataType.BOOL,    StuderAccess.READ,       StuderTarget.VIRTUAL,  None),
        (None,  "xt",  None,  None,   None,                   None,                    None,                  StuderParamException),
        (3000,  "bsp", None,  None,   None,                   None,                    None,                  StuderDatapointUnknownException),
        (9999,  None,  None,  None,   None,                   None,                    None,                  StuderDatapointUnknownException),
    ]
)
async def test_nr(nr, family, exp_nr, exp_family_id, exp_data_type, exp_access, exp_target, exp_except):
    XcomDataset.del_instance()
    dataset = await XcomDataset.async_get_instance(XcomVoltage.AC240, XcomVoltage.DC48)

    if not exp_except:
        param = dataset.get_by_nr(nr, family)

        assert param.family_id == exp_family_id
        assert param.nr == exp_nr
        assert param.data_type == exp_data_type
        assert param.access == exp_access
        assert param.target == exp_target

        if exp_data_type == StuderDataType.ENUM32:
            assert param.enum_options != None
            assert type(param.enum_options) is dict

    else:
        with pytest.raises(exp_except):
             param = dataset.get_by_nr(nr, family)



@pytest.mark.asyncio
@pytest.mark.parametrize(
    "voltageAC, voltageDC, nr, exp_unit, exp_def, exp_min, exp_max",
    [
        (XcomVoltage.AC120, XcomVoltage.DC48, 1286, "Vac", 120, 55, 140),
        (XcomVoltage.AC240, XcomVoltage.DC48, 1286, "Vac", 230, 110, 280),

        (XcomVoltage.AC120, XcomVoltage.DC12, 1108, "Vdc", 11.6, 9.0, 18.0),
        (XcomVoltage.AC120, XcomVoltage.DC24, 1108, "Vdc", 23.1, 18.0, 36.0),
        (XcomVoltage.AC120, XcomVoltage.DC48, 1108, "Vdc", 46.3, 36.0, 72.0),
        (XcomVoltage.AC240, XcomVoltage.DC12, 1108, "Vdc", 11.6, 9.0, 18.0),
        (XcomVoltage.AC240, XcomVoltage.DC24, 1108, "Vdc", 23.1, 18.0, 36.0),
        (XcomVoltage.AC240, XcomVoltage.DC48, 1108, "Vdc", 46.3, 36.0, 72.0),
    ]
)
async def test_voltage(voltageAC, voltageDC, nr, exp_unit, exp_def, exp_min, exp_max):
    XcomDataset.del_instance()
    dataset = await XcomDataset.async_get_instance(voltageAC, voltageDC)    
    
    param = dataset.get_by_nr(nr)
    assert param.unit == exp_unit
    assert param.default == exp_def
    assert param.min == exp_min
    assert param.max == exp_max


@pytest.mark.asyncio
async def test_enum():
    dataset = await XcomDataset.async_get_instance(XcomVoltage.AC240, XcomVoltage.DC48)

    param = dataset.get_by_nr(1552)
    assert param.enum_options != None
    assert type(param.enum_options) is dict
    assert len(param.enum_options) == 3

    assert param.enum_value(1) == "Slow"
    assert param.enum_value("1") == "Slow"
    assert param.enum_value(0) == "0"
    assert param.enum_value("0") == "0"

    assert param.enum_key("Slow") == 1
    assert param.enum_key("Unknown") == None
    assert param.enum_key(1) == None
    assert param.enum_key("1") == None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "family_id, exp_root_len",
    [
        ("xt",  2),
        ("l1",  0),
        ("l2",  0),
        ("l3",  0),
        ("rcc", 2),
        ("bsp", 2),
        ("bms", 2),
        ("vt",  2),
        ("vs",  2),
        ("xcom", 1),
    ]
)
async def test_menu(family_id, exp_root_len):
    dataset = await XcomDataset.async_get_instance(XcomVoltage.AC240, XcomVoltage.DC48)
    
    root_items = dataset.get_menu_items(family_id)
    assert len(root_items) == exp_root_len

    for item in root_items:
        sub_items = dataset.get_menu_items(family_id, item.id)
        assert len(sub_items) > 0

