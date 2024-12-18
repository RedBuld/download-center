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
        self.request      = request
        self.context      = context
        self.statuses     = statuses
        self.results      = results
        self.monitor      = True        

        self.status       = variables.DownloaderStatus.IDLE
        self.prev_status  = variables.DownloaderStatus.IDLE

        self.message      = ''
        self.prev_message = ''

        self.dbg_log      = ''
        self.dbg_config   = ''

        self.proc         = None
        self.temp         = variables.DownloadTempData()
        self.result       = variables.DownloadResultData()
        self.folders      = variables.DownloadFolders(
            temp    = os.path.join( self.context.temp_folder, str( self.request.task_id ) ),
            result  = os.path.join( self.context.save_folder, str( self.request.task_id ) ),
            archive = os.path.join( self.context.arch_folder, str( self.request.task_id ) )
        )

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
        self.SetStatus( variables.DownloaderStatus.WAIT )
        self.SetMessage( 'Загрузка начата' )
        asyncio.get_event_loop().run_until_complete( self.Run() )


    def CancelDownload( self, *args, **kwargs ):

        if self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            return

        self.monitor = False

        self.SetStatus( variables.DownloaderStatus.CANCELLED )

        self.SetMessage( 'Загрузка отменена' )

        logger.info( 'Downloader: stop' )

        if self.proc and self.proc.returncode is None:
            self.proc.terminate()

    ###

    async def Run( self ) -> None:
        asyncio.create_task( self.statusMonitor() )
        await asyncio.sleep( 0 )

        self.SetStatus( variables.DownloaderStatus.INIT )

        try:

            if not self.__is_status__( variables.DownloaderStatus.CANCELLED ):
                await self.Download() # can raise error

            if not self.__is_status__( variables.DownloaderStatus.CANCELLED ):
                await self.Process() # can raise error

        except Exception as e:
            traceback.print_exc()
            self.monitor = False
            await self.ProcessError( e )

        finally:
            self.monitor = False
            await self.SendResult()

            sys.exit( 0 )

    #

    async def statusMonitor( self ) -> None:
        while self.monitor:
            await self.SendStatus()
            await asyncio.sleep(5)