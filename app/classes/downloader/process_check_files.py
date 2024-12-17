import os

from .frame import DownloaderFrame

class DownloaderProcessCheckFiles( DownloaderFrame ):
    
    async def CheckFiles( self ) -> None:
        trash = []
        root_files = os.listdir( self.folders.result )

        has_pdf_files     = False
        has_audio_files   = False
        has_default_files = False

        for file in root_files:
            file_path = os.path.join( self.folders.result, file )

            # has_pdf_files     = await self.checkPDFFiles( file_path, file )

            has_audio_files   = await self.checkAudioFiles( file_path, file )

            has_default_files = await self.checkDefaultFiles( file_path, file )

            if not any( [ has_pdf_files, has_audio_files, has_default_files ] ):
                trash.append( file_path )

        for file in trash:
            os.remove( file )


    async def checkPDFFiles( self, file_path: str, file: str ) -> bool:
        return False


    async def checkAudioFiles( self, file_path: str, file: str ) -> bool:

        valid = False

        if os.path.isdir( file_path ):

            audio_folder = os.path.join( file_path, 'Audio' )

            if os.path.isdir( audio_folder ):

                audio_folder_files = os.listdir( audio_folder )

                for file in audio_folder_files:
                    file_path = os.path.join( audio_folder, file )

                    file_name, extension = os.path.splitext( file )
                    extension = extension[1:]
                    
                    if extension == self.request.format and not file_name.startswith( 'sample' ):
                        self.temp.files.append( file_path )
                        valid = True

        return valid


    async def checkDefaultFiles( self, file_path: str, file: str ) -> bool:

        valid = False

        if os.path.isfile( file_path ):

            file_name, extension = os.path.splitext( file )
            extension = extension[1:]

            if extension == 'json':
                self.temp.json = file_path
                valid = True

            elif extension == self.request.format:
                self.temp.files.append( file_path )
                valid = True

            elif extension in [ 'jpg','jpeg','png','gif' ] and file_name.endswith( '_cover' ):
                self.result.cover = file_path
                valid = True
        
        return valid