from __future__ import annotations

import sys
import os
import signal
import asyncio
import logging
import traceback
from multiprocessing import Queue
from app import dto
from app import variables

from .tools import DownloaderTools
from .step_download import DownloaderStepDownload
from .step_process import DownloaderStepProcess
from .interconnect import DownloaderInterconnect

logger = logging.getLogger('downloader-process')

def start_downloader(
        request:  dto.DownloadRequest,
        context:  variables.DownloaderContext,
        statuses: Queue,
        results:  Queue
    ):
    _downloader = Downloader(
        request  = request,
        context  = context,
        statuses = statuses,
        results  = results
    )
    _downloader.StartDownload()

class Downloader(
    DownloaderTools,
    DownloaderInterconnect,
    DownloaderStepDownload,
    DownloaderStepProcess,
):

    def __init__(
        self,
        request:  dto.DownloadRequest,
        context:  variables.DownloaderContext = None,
        statuses: Queue = None,
        results:  Queue = None,
    ) -> None:
        self.request   = request
        self.context   = context
        self.statuses  = statuses
        self.results   = results
        
        self.done       = False
        self.cancelled  = False

        self.step         = variables.DownloaderStep.IDLE
        self.prev_step    = variables.DownloaderStep.IDLE

        self.message      = ''
        self.prev_message = ''

        self.dbg_log    = ''
        self.dbg_config = ''

        self.proc    = None
        self.temp    = variables.DownloadTempData()
        self.result  = variables.DownloadResultData()
        self.folders = variables.DownloadFolders(
            temp    = os.path.join( self.context.temp_folder, str( self.request.task_id ) ),
            result  = os.path.join( self.context.save_folder, str( self.request.task_id ) ),
            archive = os.path.join( self.context.arch_folder, str( self.request.task_id ) )
        )

        self.decoder    = 'utf-8'
        self.file_limit = 1_549_000_000

        signal.signal( signal.SIGINT, self.CancelDownload )
        signal.signal( signal.SIGTERM, self.CancelDownload )

    ###

    def StartDownload( self ) -> None:
        # 
        logging.basicConfig(
            format='%(levelname)s: %(name)s[%(process)d] %(asctime)s - %(message)s',
            level=logging.INFO
        )
        logger.info( 'Downloader: Start' )
        self.SetStep( variables.DownloaderStep.WAIT )
        self.SetMessage( 'Загрузка начата' )
        asyncio.get_event_loop().run_until_complete( self.Run() )


    def CancelDownload( self, *args, **kwargs ):

        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return

        self.cancelled = True

        self.done = True

        self.SetStep( variables.DownloaderStep.CANCELLED )

        self.SetMessage( 'Загрузка отменена' )

        logger.info( 'Downloader: stop' )

        if self.proc and self.proc.returncode is None:
            self.proc.terminate()

    ###

    async def Run( self ) -> None:
        asyncio.create_task( self.statusRunner() )
        await asyncio.sleep( 0 )

        self.SetStep( variables.DownloaderStep.INIT )

        try:

            if not self.cancelled:
                await self.Download() # can raise error

            if not self.cancelled:
                await self.Process() # can raise error

        except Exception as e:
            traceback.print_exc()
            self.done = True
            await self.ProcessError( e )

        finally:
            self.done = True
            await self.SendResult()

            sys.exit( 0 )

    #

    async def statusRunner( self ) -> None:
        while not self.done:
            await self.SendStatus()
            await asyncio.sleep(5)