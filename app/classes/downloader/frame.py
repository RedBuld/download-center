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
    proc:            asyncio.subprocess.Process

    temp:            variables.DownloadTempData
    result:          variables.DownloadResultData
    folders:         variables.DownloadFolders

    done:            bool = False
    cancelled:       bool = False

    step:            int = variables.DownloaderStep.IDLE
    prev_step:       int = variables.DownloaderStep.IDLE
    
    message:         str = ''
    prev_message:    str = ''

    dbg_log:         str = ''
    dbg_config:      str = ''

    decoder:         str = 'utf-8'

    def __repr__( self ) -> str:
        return str( {
            'request':         self.request,
            'context':         self.context,
            'temp':            self.temp,
            'result':          self.result,
            'folders':         self.folders,
            'proc':            self.proc,
            'done':            self.done,
            'cancelled':       self.cancelled,
            'step':            self.step,
            'prev_step':       self.prev_step,
            'message':         self.message,
            'prev_message':    self.prev_message,
        } )

    def __is_step__(
        self,
        check_step: int
    ) -> bool:
        return self.step == check_step
    
    def __debug_config__( self ) -> str:
        return ujson.dumps( {
            'request': self.request.__export__(),
            'context': self.context.__export__(),
            'temp':    self.temp.__export__(),
        }, indent=4, ensure_ascii=False )

    #

    def SetStep(
        self,
        new_step: int
    ) -> None:
        self.prev_step = self.step
        self.step = new_step

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