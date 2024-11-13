from dataclasses import dataclass, field

from .global_config import *
from .downloader_config import *
from .queue_config import *
from .queue_stats import *
from .queue_waiting import *
from .queue_running import *
from .queue_sites_groups import *

@dataclass(frozen=True)
class DownloaderStep():
	CANCELLED = 99
	ERROR = 98
	IDLE = 0
	WAIT = 1
	INIT = 2
	RUNNING = 3
	PROCESSING = 4
	DONE = 5

@dataclass(init=False, slots=True)
class DownloaderTemp():
    text: str               = ""
    cover: str              = ""
    source_files: List[str] = field(default_factory=list)
    result_files: List[str] = field(default_factory=list)
    chapters: int           = 0
    orig_size: int          = 0
    oper_size: int          = 0
    author: str             = ""
    name: str               = ""

    def __init__( self ) -> None:
        self.text         = ""
        self.cover        = ""
        self.source_files = []
        self.result_files = []
        self.chapters     = 0
        self.orig_size    = 0
        self.oper_size    = 0
        self.author       = ""
        self.name         = ""