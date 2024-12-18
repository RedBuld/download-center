import os
import asyncio
import subprocess

from .frame import DownloaderFrame

class DownloaderProcessFiles( DownloaderFrame ):

    async def ProcessFiles( self ) -> None:

        preselected_archiver = None
        for key, executable in self.context.compression.items():
            if os.path.exists( executable[ 'bin' ] ):
                preselected_archiver = key

        if len( self.temp.files ) > 0:

            for original_file in self.temp.files:

                size = os.path.getsize( original_file )
                self.result.orig_size += size

                if size < self.context.file_limit:
                    self.result.files.append( original_file )

                else:
                    os.makedirs( self.folders.archive, exist_ok=True )

                    file = os.path.basename( original_file )
                    file_name, _ = os.path.splitext( file )

                    target_archive = os.path.join( self.folders.archive, f'{file_name}' )

                    if preselected_archiver:

                        split_file_size = int( self.context.file_limit / 1000 / 1000 )
                        split_file_size = f'{split_file_size}m'

                        if preselected_archiver == 'zip':
                            args = [f'-s{split_file_size}', '-0', target_archive, original_file ]

                        elif preselected_archiver == 'rar':
                            args = [ 'a' , f'-v{split_file_size}', '-ep', '-m0', target_archive, original_file ]

                        elif preselected_archiver == '7z':
                            args = [ 'a' , f'-v{split_file_size}', '-mx0', target_archive, original_file ]

                        self.proc = await asyncio.create_subprocess_exec(
                            self.context.compression[ preselected_archiver ][ 'bin' ],
                            *args,
                            cwd    = self.context.compression[ preselected_archiver ][ 'cwd' ],
                            env    = dict( os.environ ),
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE
                        )
                        await self.proc.wait()

                        if self.proc.returncode == 0:
                            try:
                                os.remove( original_file )
                            except:
                                pass
                        else:
                            error = await self.proc.stdout.read()
                            error += await self.proc.stderr.read()
                            if error:
                                raise Exception( error.decode( 'utf-8', errors='replace' ) )
                            else:
                                raise ChildProcessError( 'Процесс архивации неожиданно завершился' )

        if os.path.exists( self.folders.archive ):
            archives = os.listdir( self.folders.archive )

            for archive in archives:

                archive_path = os.path.join( self.folders.archive, archive )

                self.result.files.append( archive_path )
                self.result.oper_size += os.path.getsize( archive_path )