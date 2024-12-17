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

        if self.cancelled:
            return

        self.SetStep( variables.DownloaderStep.PROCESSING )
        self.SetMessage( 'Обработка файлов' )

        await self.CheckFiles()

        if self.cancelled:
            return

        await self.RenameFiles()

        if self.cancelled:
            return

        await self.ProcessFiles()

        if self.cancelled:
            return

        await self.ProcessJSON()

        if self.cancelled:
            return

        await self.ProcessHashtags()

        if self.cancelled:
            return

        await self.ProcessChapters()

        if self.cancelled:
            return

        await self.ProcessCaption()

        if self.cancelled:
            return

        self.SetStep( variables.DownloaderStep.DONE )
        self.SetMessage( 'Выгрузка файлов' )