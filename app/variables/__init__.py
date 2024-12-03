from dataclasses import dataclass, field

from .global_config import *
from .downloader_config import *
from .queue_config import *
from .queue_stats import *
from .queue_waiting import *
from .queue_running import *
from .queue_sites_groups import *

class WaitingLimitException(Exception):
    pass

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
    chapters_total: int     = 0
    chapters_valid: int     = 0
    chapters_start: int     = 0
    chapters_end: int       = 0
    first_chapter_name: str = ''
    last_chapter_name: str  = ''
    chapters_end: int       = 0
    orig_size: int          = 0
    oper_size: int          = 0
    author: str             = ""
    name: str               = ""

    def __init__( self ) -> None:
        self.text               = ""
        self.cover              = ""
        self.source_files       = []
        self.result_files       = []
        self.chapters_total     = 0
        self.chapters_valid     = 0
        self.chapters_start     = 0
        self.chapters_end       = 0
        self.first_chapter_name = ""
        self.last_chapter_name  = ""
        self.orig_size          = 0
        self.oper_size          = 0
        self.author             = ""
        self.name               = ""