import asyncio
import ujson
import logging
from multiprocessing import Queue
from typing import Any

from app import dto
from app import variables

logger = logging.getLogger('downloader-process')

class DownloaderFrame:
    request:         dto.DownloadRequest
    context:         variables.DownloaderContext
    statuses:        Queue
    results:         Queue
    monitor:         bool = True

    status:          int = variables.DownloaderStatus.IDLE
    prev_status:     int = variables.DownloaderStatus.IDLE
    
    message:         str = ''
    prev_message:    str = ''

    dbg_log:         str = ''
    dbg_config:      str = ''

    temp:            variables.DownloadTempData
    result:          variables.DownloadResultData
    folders:         variables.DownloadFolders
    proc:            asyncio.subprocess.Process

    def __repr__( self ) -> str:
        return str( {
            'request':         self.request,
            'context':         self.context,
            'temp':            self.temp,
            'result':          self.result,
            'folders':         self.folders,
            'proc':            self.proc,
            'status':          self.status,
            'prev_status':     self.prev_status,
            'message':         self.message,
            'prev_message':    self.prev_message,
        } )

    def __is_status__(
        self,
        check_status: int
    ) -> bool:
        return self.status == check_status
    
    def __debug_config__( self ) -> str:
        return ujson.dumps( {
            'request': self.request.__export__(),
            'context': self.context.__export__(),
            'temp':    self.temp.__export__(),
        }, indent=4, ensure_ascii=False )

    #

    def SetStatus(
        self,
        new_status: int
    ) -> None:
        self.prev_status = self.status
        self.status = new_status

    def SetMessage(
        self,
        new_message: str
    ) -> None:
        self.prev_message = self.message
        self.message = new_message
    
    def PrintLog(
        self,
        message: Any
    ) -> None:
        logger.info( str( message ) )