import os
import shutil

from app import variables
from app import dto

from .frame import DownloaderFrame

class DownloaderInterconnect( DownloaderFrame ):

    async def SendStatus( self ) -> None:

        if self.message == self.prev_message:
            return

        self.SetMessage( self.message )

        status = dto.DownloadStatus(
            task_id    = self.request.task_id,
            user_id    = self.request.user_id,
            bot_id     = self.request.bot_id,
            web_id     = self.request.web_id,
            chat_id    = self.request.chat_id,
            message_id = self.request.message_id,
            text       = self.message,
            status     = self.status,
        )

        self.statuses.put( status.model_dump() )


    async def SendResult( self ) -> None:

        if self.folders.temp and os.path.exists( self.folders.temp ):
            try:
                shutil.rmtree( self.folders.temp )
            except:
                pass

        if self.__is_status__( variables.DownloaderStatus.ERROR ) or self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            self.result.cover = ''
            self.temp.files = []
            if self.folders.result and os.path.exists( self.folders.result ):
                try:
                    shutil.rmtree( self.folders.result )
                except:
                    pass

        if self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            return
        
        if self.__is_status__( variables.DownloaderStatus.ERROR ):
            self.dbg_config = self.__debug_config__()
        else:
            self.dbg_log = None
        
        result = dto.DownloadResult(
            task_id    = self.request.task_id,
            user_id    = self.request.user_id,
            bot_id     = self.request.bot_id,
            web_id     = self.request.web_id,
            chat_id    = self.request.chat_id,
            message_id = self.request.message_id,
            site       = self.request.site,
            proxy      = self.request.proxy,
            url        = self.request.url,
            format     = self.request.format,
            start      = self.request.start,
            end        = self.request.end,
            status     = self.status,
            text       = self.result.caption,
            cover      = self.result.cover,
            files      = self.result.files,
            orig_size  = self.result.orig_size,
            oper_size  = self.result.oper_size,
            dbg_log    = self.dbg_log,
            dbg_config = self.dbg_config
        )

        self.results.put( result.model_dump() )