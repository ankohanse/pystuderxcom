from typing import Literal
import pytest
import pytest_asyncio
from pystuderxcom import StuderDataType, StuderUserLevel
from pystuderxcom import XcomVoltage, XcomUserLevel
from pystuderxcom.datapoints import XcomDatapoint


@pytest.mark.parametrize(
    "fixture, inp_str, inp_def, exp_val, exp_except",
    [
        ("120 VAC", "120 VAC", None, XcomVoltage.AC120, None),
        ("120_VAC", "120_VAC", None, XcomVoltage.AC120, None),
        ("240 VAC", "240 VAC", None, XcomVoltage.AC240, None),
        ("240_VAC", "240_VAC", None, XcomVoltage.AC240, None),
        ("12 VDC", "12 VDC", None, XcomVoltage.DC12, None),
        ("12_VDC", "12_VDC", None, XcomVoltage.DC12, None),
        ("24 VDC", "24 VDC", None, XcomVoltage.DC24, None),
        ("24_VDC", "24_VDC", None, XcomVoltage.DC24, None),
        ("48 VDC", "48 VDC", None, XcomVoltage.DC48, None),
        ("48_VDC", "48_VDC", None, XcomVoltage.DC48, None),

        ("value",   "120 VAC", XcomVoltage.AC240, XcomVoltage.AC120, None),
        ("default", "xxxxxxx", XcomVoltage.AC120, XcomVoltage.AC120, None),
        ("default", "xxxxxxx", XcomVoltage.AC240, XcomVoltage.AC240, None),
        ("value",   "12 VDC", XcomVoltage.DC24, XcomVoltage.DC12, None),
        ("default", "xxxxxx", XcomVoltage.DC12, XcomVoltage.DC12, None),
        ("default", "xxxxxx", XcomVoltage.DC24, XcomVoltage.DC24, None),
        ("default", "xxxxxx", XcomVoltage.DC48, XcomVoltage.DC48, None),
        ("except",  "xxxxxx", None,          None,          Exception),
    ]
)
def test_voltage(fixture:str, inp_str:str, inp_def: XcomVoltage|None, exp_val: XcomVoltage|None, exp_except: type[Exception]|None):

    if exp_except is None:
        val = XcomVoltage.from_str(inp_str, inp_def)
        assert val == exp_val
        assert type(val) is XcomVoltage
    else:
        with pytest.raises(exp_except):
            val = XcomVoltage.from_str(inp_str, inp_def)


@pytest.mark.parametrize(
    "fixture, inp_str, inp_def, exp_val, exp_except",
    [
        ("INFO",    "INFO",   None, StuderUserLevel.INFO,      None),
        ("VO",      "VO",     None, StuderUserLevel.VIEWONLY,  None),
        ("V.O.",    "V.O.",   None, StuderUserLevel.VIEWONLY,  None),
        ("BASIC",   "BASIC",  None, StuderUserLevel.BASIC,     None),
        ("EXPERT",  "EXPERT", None, StuderUserLevel.EXPERT,    None),
        ("INST",    "INST",   None, StuderUserLevel.INSTALLER, None),
        ("INST.",   "INST.",  None, StuderUserLevel.INSTALLER, None),
        ("QSP",     "QSP",    None, StuderUserLevel.STUDER,    None),

        ("value",   "EXPERT", StuderUserLevel.BASIC, StuderUserLevel.EXPERT, None),
        ("default", "xxxxxx", StuderUserLevel.BASIC, StuderUserLevel.BASIC,  None),
        ("except",  "xxxxxx", None,        None,         Exception),
    ]
)
def test_user_level(fixture:str, inp_str:str, inp_def: StuderUserLevel|None, exp_val: StuderUserLevel|None, exp_except: type[Exception]|None):

    if exp_except is None:
        val = XcomUserLevel.from_str(inp_str, inp_def)
        assert val == exp_val
        assert type(val) is StuderUserLevel
    else:
        with pytest.raises(exp_except):
            val = XcomUserLevel.from_str(inp_str, inp_def)
