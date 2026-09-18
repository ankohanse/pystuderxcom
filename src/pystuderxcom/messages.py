##
## Class implementing Xcom protocol 
##
## See the studer document: "Technical Specification - Xtender serial protocol"
## Download from:
##   https://studer-innotec.com/downloads/ 
##   -> Downloads -> software + updates -> communication protocol xcom 232i
##

import logging

from aiofiles import open as aiofiles_open
from dataclasses import dataclass

import orjson

from pystuderxcom.shared.helpers import HybridLock
from pystuderxcom.shared.studer_messageset import StuderMessageDef, StuderMessageSet, StuderMessageSyntaxException, StuderMessageUnknownException


from .shared.studer_types import (
    StuderUserLevel,
)
from .const import (
    XcomUserLevel
)
from .data import (
    XcomDataMessageRsp,
)



_LOGGER = logging.getLogger(__name__)


@dataclass
class XcomMessageDef(StuderMessageDef):
    # From parent class:
    #   level: StuderUserLevel
    #   number: int
    #   string: str

    @staticmethod
    def from_dict(d):
        lvl = d.get('lvl', None)
        nr  = d.get('nr', None)
        msg = d.get('msg', None)

        # Check and convert properties
        if "_rem" in d and len(d)==1:
            return None # Line only contains a comment
        
        if lvl is None or nr is None or msg is None:
            raise StuderMessageSyntaxException(f"Missing required field in messageset; lvl={lvl}, nr={nr}, msg={msg}")
        
        if not isinstance(nr, int):
            raise StuderMessageSyntaxException(f"Unexpected field type in messageset, expected int; lvl={lvl}, nr={nr}, msg={msg}")
        
        level = XcomUserLevel.from_str(str(lvl))
        number = int(nr)
        string = str(msg).strip()
            
        return XcomMessageDef(
            level = level, 
            number = number, 
            string = string
        )
        

class XcomMessageSet(StuderMessageSet):

    # Paths to all files definining the messages
    PATH_EN = __file__.replace('.py', '_en.json')


    def __init__(self):
        raise RuntimeError("Use 'XcomMessageSet.get_instance()' or 'await XcomMessageSet.async_get_instance()' instead of direct instantiation.")


    # Single instance of the NextDataset
    _instance = None
    _instance_lock = HybridLock()

    @classmethod
    async def async_get_instance(cls, language: str = "en") -> 'XcomMessageSet':
        """
        Async helper function to get singleton instance of XcomMessageSet
        """
        async with cls._instance_lock:
            if cls._instance is None:
                # Create a bare instance without calling __init__
                self = super().__new__(cls)
                await self._async_init(language)
                cls._instance = self

        return cls._instance

    @classmethod
    def get_instance(cls, language: str = "en") -> 'XcomMessageSet':
        """
        Sync helper function to get singleton instance of NextDataset
        """
        with cls._instance_lock:
            if cls._instance is None:
                # Create a bare instance without calling __init__
                self = super().__new__(cls)
                self._init(language)
                cls._instance = self
            
        return cls._instance

    @classmethod
    def del_instance(cls):
        """Used for intermediate cleanup during unit tests"""
        cls._instance = None


    async def _async_init(self, language: str = "en"):
        """
        The actual XcomMessage list is kept in a separate json file.
        """
        match language:
            case "en": path = XcomMessageSet.PATH_EN # English
            case _:
                msg = f"Unknown language: '{language}'"
                raise Exception(msg)
        
        async with aiofiles_open(path, "r", encoding="UTF-8") as f:
            text = await f.read()
        
        values = orjson.loads(text)
        messages = list(filter(None, [XcomMessageDef.from_dict(val) for val in values]))

        super().__init__(messages)


    def _init(self, language: str = "en"):
        """
        The actual XcomMessage list is kept in a separate json file.
        """
        match language:
            case "en": path = XcomMessageSet.PATH_EN # English
            case _:
                msg = f"Unknown language: '{language}'"
                raise Exception(msg)
        
        with open(path, "r", encoding="UTF-8") as f:
            text = f.read()
        
        values = orjson.loads(text)
        messages = list(filter(None, [XcomMessageDef.from_dict(val) for val in values]))

        super().__init__(messages)
   

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
            return self._msg_set.str_by_nr(self.message_number)
        except:
            return f"({self.message_number}): unknown message"
    

