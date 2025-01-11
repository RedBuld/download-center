import io
from dataclasses import dataclass, field

from .exceptions import *
from .global_config import *
from .downloader_config import *
from .queue_config import *
from .queue_stats import *
from .queue_waiting import *
from .queue_running import *
from .queue_sites_groups import *

@dataclass(frozen=True)
class DownloaderStatus():
	CANCELLED = 99
	ERROR = 98
	IDLE = 0
	WAIT = 1
	INIT = 2
	RUNNING = 3
	PROCESSING = 4
	DONE = 5


@dataclass(slots=True)
class DownloadFolders:
    temp:    str = ''
    result:  str = ''
    archive: str = ''


@dataclass(init=False, slots=True)
class DownloadTempData:
    json:           str = ''
    cover:          str = ''
    thumb:          io.BytesIO | None = None
    files:          List[ str ] = field( default_factory=list )
    # src
    authors:        List[ str ] = field( default_factory=list )
    hashtags:       List[ str ] = field( default_factory=list )
    chapters:       str = ''
    # meta
    chapters_total: int = 0
    chapters_valid: int = 0
    chapters_start: int = 0
    chapters_end:   int = 0
    first_chapter:  str = ''
    last_chapter:   str = ''
    # rename files ( next updates )
    book_url:       str = ''
    book_title:     str = ''
    book_author:    str = ''
    seria_url:      str = ''
    seria_name:     str = ''
    seria_number:   str = ''

    def __init__( self ) -> None:
        self.json           = ''
        self.cover          = ''
        self.files          = []
        #
        self.authors        = []
        self.hashtags       = []
        self.chapters       = ''
        #
        self.chapters_total = 0
        self.chapters_valid = 0
        self.chapters_start = 0
        self.chapters_end   = 0
        self.first_chapter  = ''
        self.last_chapter   = ''
        #
        self.book_url       = ''
        self.book_title     = ''
        self.book_author    = ''
        self.seria_url      = ''
        self.seria_name     = ''
        self.seria_number   = ''
    
    def __export__( self) -> Dict:
        return {
            'authors':        self.authors,
            'hashtags':       self.hashtags,
            'chapters':       self.chapters,
            'chapters_total': self.chapters_total,
            'chapters_valid': self.chapters_valid,
            'chapters_start': self.chapters_start,
            'chapters_end':   self.chapters_end,
            'first_chapter':  self.first_chapter,
            'last_chapter':   self.last_chapter,
            'book_url':       self.book_url,
            'book_title':     self.book_title,
            'book_author':    self.book_author,
            'seria_url':      self.seria_url,
            'seria_name':     self.seria_name,
            'seria_number':   self.seria_number,
        }
         

@dataclass(init=False, slots=True)
class DownloadResultData:
    caption:   str = ''
    cover:     str = ''
    thumb:     str = ''
    files:     List[str] = field(default_factory=list)
    orig_size: int = 0
    oper_size: int = 0

    def __init__( self ) -> None:
        self.caption   = ''
        self.cover     = ''
        self.thumb     = ''
        self.files     = []
        self.orig_size = 0
        self.oper_size = 0
    
    def __export__( self) -> Dict:
        return {
            'caption':   self.caption,
            'cover':     self.cover,
            'thumb':     self.thumb,
            'files':     self.files,
            'orig_size': self.orig_size,
            'oper_size': self.oper_size,
        }