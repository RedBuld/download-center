import os

from .frame import DownloaderFrame

class DownloaderProcessRenameFiles( DownloaderFrame ):

    async def RenameFiles( self ) -> None:

        if self.request.format == 'pdf':
            await self.renamePDFFiles()

        elif self.request.format == 'mp3':
            await self.renameAudioFiles()

        else:
            await self.renameDefaultFiles()


    async def renamePDFFiles( self ) -> None:

        files = []
        index = 1
        need_index = len( self.temp.files ) > 1

        for file in self.temp.files:
            original_file = file

            path, file = os.path.split( original_file )
            _, extension = os.path.splitext( file )

            new_name = f"{self.temp.book_author} - {self.temp.book_title}" + (f" ({index})" if need_index else '') + extension
            new_file = os.path.join( path, new_name )

            os.rename( original_file, new_file )

            files.append( new_file )
            index += 1
        
        self.temp.files = files


    async def renameAudioFiles( self ) -> None:

        files = []
        index = 1
        need_index = len( self.temp.files ) > 1

        for file in self.temp.files:
            original_file = file

            path, file = os.path.split( original_file )
            _, extension = os.path.splitext( file )

            new_name = f"{self.temp.book_author} - {self.temp.book_title}" + (f" ({index})" if need_index else '') + extension
            new_file = os.path.join( path, new_name )

            os.rename( original_file, new_file )

            files.append( new_file )
            index += 1
        
        self.temp.files = files


    async def renameDefaultFiles( self ) -> None:

        suffix = ''

        files = []
        index = 1
        need_index = len( self.temp.files ) > 1

        if self.request.start or self.request.end:

            _chapters = self.temp.chapters_total

            if _chapters > 0:
                _start = int( self.request.start )
                _end = int( self.request.end )

                if _start != 0 and _end != 0:
                    suffix = f'-from-{_start}-to-{_end}'

                elif _start != 0 and _end == 0:
                    if _start > 0:
                        _end = _start + _chapters
                        suffix = f'-from-{_start}-to-{_end}'
                    else:
                        suffix = f'-last-{abs( _start )}'

                elif _end != 0 and _start == 0:
                    suffix = f'-from-1-to-{_chapters}'

        if suffix != '':

            for original_file in self.temp.files:
            
                path, file = os.path.split( original_file )
                old_name, extension = os.path.splitext( file )

                new_name = old_name + suffix + (f" ({index})" if need_index else '') + extension
                new_file = os.path.join( path, new_name )

                os.rename( original_file, new_file )

                files.append( new_file )
                index += 1

                self.temp.files = files