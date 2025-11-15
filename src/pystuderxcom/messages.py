##
## Class implementing Xcom protocol 
##
## See the studer document: "Technical Specification - Xtender serial protocol"
## Download from:
##   https://studer-innotec.com/downloads/ 
##   -> Downloads -> software + updates -> communication protocol xcom 232i
##

import logging

from dataclasses import dataclass

from .const import (
    XcomLevel,
)
from .data import (
    XcomDataMessageRsp,
)


_LOGGER = logging.getLogger(__name__)


@dataclass
class XcomMessageDef:
    PATH_EN = __file__.replace('.py', '_en.json')

    level: XcomLevel
    number: int
    string: str

    @staticmethod
    def from_dict(d):
        lvl = d.get('lvl', None)
        nr  = d.get('nr', None)
        msg = d.get('msg', None)

        # Check and convert properties
        if lvl is None or nr is None or msg is None:
            return None
        
        if type(nr) is not int:
            return None
        
        level = XcomLevel.from_str(str(lvl))
        number = int(nr)
        string = str(msg).strip()
            
        return XcomMessageDef(level, number, string)
        

class XcomMessageUnknownException(Exception):
    pass


class XcomMessageSet():

    def __init__(self, messages: list[XcomMessageDef] | None = None):
        self._messages = messages
   

    def getByNr(self, nr: int) -> XcomMessageDef:
        for msg in self._messages:
            if msg.number == nr:
                return msg

        raise XcomMessageUnknownException(nr)


    def getStringByNr(self, nr: int) -> str:
        msg = self.getByNr(nr)
        return msg.string


class XcomMessage(XcomDataMessageRsp):

    def __init__(self, rsp: XcomDataMessageRsp, msg_set: XcomMessageSet):

        super().__init__(
            message_total = rsp.message_total,
            message_number = rsp.message_number,
            source_address = rsp.source_address,
            timestamp = rsp.timestamp,
            value = rsp.value,
        )
        self._msg_set = msg_set


    @property
    def message_string(self):
        try:
            return self._msg_set.getStringByNr(self.message_number)
        except:
            return f"({self.message_number}): unknown message"
    

