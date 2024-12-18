from app import variables

from .process_check_files import DownloaderProcessCheckFiles
from .process_rename_files import DownloaderProcessRenameFiles
from .process_files import DownloaderProcessFiles
from .process_json import DownloaderProcessJSON
from .process_hashtags import DownloaderProcessHashtags
from .process_chapters import DownloaderProcessChapters
from .process_caption import DownloaderProcessCaption

class DownloaderStepProcess(
    DownloaderProcessCheckFiles,
    DownloaderProcessRenameFiles,
    DownloaderProcessFiles,
    DownloaderProcessJSON,
    DownloaderProcessHashtags,
    DownloaderProcessChapters,
    DownloaderProcessCaption,
):
    
    async def Process( self ) -> None:


        if self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            return


        self.SetStatus( variables.DownloaderStatus.PROCESSING )
        self.SetMessage( 'Обработка файлов' )


        actions_queue = [
            self.CheckFiles,
            self.RenameFiles,
            self.ProcessFiles,
            self.ProcessJSON,
            self.ProcessHashtags,
            self.ProcessChapters,
            self.ProcessCaption
        ]


        for action in actions_queue:
            if self.__is_status__( variables.DownloaderStatus.CANCELLED ):
                return
            await action()


        self.SetStatus( variables.DownloaderStatus.DONE )
        self.SetMessage( 'Выгрузка файлов' )