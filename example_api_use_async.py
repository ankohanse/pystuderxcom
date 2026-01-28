import asyncio
import logging
import sys

from pystuderxcom import AsyncXcomApiTcp, XcomApiTcp, XcomApiTcpMode
from pystuderxcom import AsyncXcomFactory, XcomFactory
from pystuderxcom import XcomDataset, XcomDatapoint, XcomData, XcomValues, XcomValuesItem
from pystuderxcom import XcomVoltage, XcomAggregationType, XcomFormat
from helper import RunHelper

# Setup logging to StdOut
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    dataset = await AsyncXcomFactory.create_dataset(XcomVoltage.AC240, XcomVoltage.DC48) # or use XcomVoltage.AC120, XcomVoltage.DC12 or XcomVoltage.DC24 
    info_3021 = dataset.get_by_nr(3021, "xt")  # the "xt" part is optional but usefull for detecting mistakes
    info_3022 = dataset.get_by_nr(3022, "xt")
    info_3023 = dataset.get_by_nr(3023, "xt")
    info_7002 = dataset.get_by_nr(7002, "bsp")
    param_5012 = dataset.get_by_nr(5012, "rcc")
    param_1107 = dataset.get_by_nr(1107, "xt")

    # When Moxa is configured as TCP Client (preferred mode):
    # api = AsyncXcomApiTcp(mode=XcomApiTcpMode.SERVER, listen_port=4001)                               
    #
    # When Moxa is configured as TCP Server:
    # api = AsyncXcomApiTcp(mode=XcomApiTcpMode.CLIENT, remote_ip=<moxa_ip>, remote_port=<moxa_port>)   
    #
    # When Moxa is configured as UDP:
    # api = AsyncXcomApiUdp(remote_ip=<moxa_ip>, remote_port=<moxa_port>, local_port=4001)

    api = AsyncXcomApiTcp(mode=XcomApiTcpMode.SERVER, listen_port=4001)    # port number configured in Xcom-LAN/Moxa NPort
    try:
        if not await api.start():
            logger.info(f"Did not connect to Xcom")
            return

        # Retrieve individual infos and params
        logger.info(f"")
        logger.info(f"Retrieve infos and params via individual calls")

        # Retrieve info #3023 from the first Xtender (Output power)
        value = await api.request_value(info_3023, "XT1")    # xt address range is 101 to 109, or use "XT1" to "XT9"
        logger.info(f"XT1 {info_3023.nr}: {value} {info_3023.unit or ''} ({info_3023.name})")

        # Retrieve info #7002 from BSP (State of Charge)
        value = await api.request_value(info_7002, "BSP")    # bsp address range is only 601, or use "BSP"
        logger.info(f"BSP {info_7002.nr}: {value} {info_7002.unit or ''} ({info_7002.name})")

        # Retrieve param #5012 from RCC (User Level)
        value = await api.request_value(param_5012, "RCC")    # rcc address range is only 501, or use "RCC"
        logger.info(f"RCC {param_5012.nr}: {param_5012.enum_value(value)} {param_5012.unit or ''} ({param_5012.name})")

        # Retrieve multiple values (any combination of infos or params) in one call.
        logger.info(f"")
        logger.info(f"Retrieve multiple infos and params in one call")

        req = XcomValues([
            XcomValuesItem(dataset.get_by_nr(1107, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(1381, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(1382, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(1442, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(1443, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(1444, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3020, "xt"), code="XT1"),  # xt range is address=101 to 109, or use code="XT1" to "XT9"
            XcomValuesItem(dataset.get_by_nr(3028, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3031, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3032, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3049, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3078, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3081, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3083, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3101, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3104, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(3119, "xt"), code="XT1"),
            XcomValuesItem(dataset.get_by_nr(5002, "rcc"), code="RCC"),
            XcomValuesItem(dataset.get_by_nr(5012, "rcc"), code="RCC"),
            XcomValuesItem(dataset.get_by_nr(5101, "rcc"), code="RCC"),
            XcomValuesItem(dataset.get_by_nr(7007, "bsp"), code="BSP"),
            XcomValuesItem(dataset.get_by_nr(7008, "bsp"), code="BSP"),
            XcomValuesItem(dataset.get_by_nr(7030, "bsp"), code="BSP"),
            XcomValuesItem(dataset.get_by_nr(7031, "bsp"), code="BSP"),
            XcomValuesItem(dataset.get_by_nr(7032, "bsp"), code="BSP"),
            XcomValuesItem(dataset.get_by_nr(7033, "bsp"), code="BSP"),
        ])
        rsp = await api.request_values(req)
        if rsp:
            for item in rsp.items:
                item_value = item.value if item.datapoint.format not in [XcomFormat.LONG_ENUM, XcomFormat.SHORT_ENUM] else item.datapoint.enum_value(item.value)

                logger.info(f"Values {item.code} {item.datapoint.nr}: {item_value} {item.datapoint.unit or ''} ({item.datapoint.name})")

        # Retrieve multiple infos in one call and perform aggregation.
        # Cannot be used on params.
        # This requires at least firmware version 1.6.74 on your Xcom-232i/Xcom-LAN.
        logger.info(f"")
        logger.info(f"Retrieve multiple infos with aggregation in one call")
        try:
            req = XcomValues([
                XcomValuesItem(info_3021, aggregation_type=XcomAggregationType.SUM),      
                XcomValuesItem(info_3022, aggregation_type=XcomAggregationType.AVERAGE),  
            ])
            rsp = await api.request_infos(req)
            if rsp:
                logger.info(f"Infos flags: {rsp.flags}")
                logger.info(f"Infos datetime: {rsp.datetime}")
                for item in rsp.items:
                    item_code = item.code if item.code is not None else str(item.aggregation_type)
                    item_value = item.value if item.datapoint.format not in [XcomFormat.LONG_ENUM, XcomFormat.SHORT_ENUM] else item.datapoint.enum_value(item.value)

                    logger.info(f"Infos {item_code} {item.datapoint.nr}: {item.value} {item.datapoint.unit or ''} ({item.datapoint.name})")

        except Exception as ex:
            logger.warning(ex)

        # Retrieve and Update param 1107 on the first Xtender (Maximum current of AC source)
        # Note the the change is written into RAM memory; a subsequent request_value will be taken 
        # from Flash memory and will not show the change. During its operation the Xtender will 
        # still use the updated value from RAM (until a full restart of the Xtender).
        logger.info(f"")
        logger.info(f"Retrieve and then update a param")

        value = await api.request_value(param_1107, "XT1")
        logger.info(f"XT1 {param_1107.nr}: {value} {param_1107.unit} ({param_1107.name})")

        value = 3.0    # 4 Ampere
        if await api.update_value(param_1107, value, "XT1"):
            logger.info(f"XT1 {param_1107.nr} updated to {value} {param_1107.unit} ({param_1107.name})")

    except Exception as e:
        logger.info(f"Unexpected exception: {str(e)}")

    finally:
        logger.info(f"")
        await api.stop()



RunHelper.run(main)  # main loop