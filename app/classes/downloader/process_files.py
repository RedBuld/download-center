import os
import math
import asyncio
import subprocess
import logging
import traceback
from PIL import Image, ImageFilter

from .frame import DownloaderFrame

logger = logging.getLogger('downloader-process')

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

        use_thumb = self.request.thumb

        logger.info( str( use_thumb ) )

        if os.path.exists( self.folders.archive ):
            use_thumb = False
            archives = os.listdir( self.folders.archive )

            for archive in archives:

                archive_path = os.path.join( self.folders.archive, archive )

                self.result.files.append( archive_path )
                self.result.oper_size += os.path.getsize( archive_path )
        
        logger.info( str( use_thumb ) )

        if self.temp.cover:
            if self.request.cover:
                self.result.cover = self.temp.cover
            if use_thumb:
                thumb_path = self.temp.cover.replace('cover','thumb')
                thumb_dimension = 320
                try:
                    with Image.open( self.temp.cover ) as img_src:
                        # create result image
                        img_result = Image.new('RGB', ( thumb_dimension, thumb_dimension ) )

                        # resize original image
                        img_src.thumbnail( ( thumb_dimension, thumb_dimension ) )

                        # copy thumb to bg layer
                        img_bg = img_src.copy()

                        # find maximal resize scale coefficient
                        resize_coef = max( thumb_dimension / img_src.width, thumb_dimension / img_src.height )
                        
                        # calculate resize dimension
                        resize_dimension = math.ceil( thumb_dimension * resize_coef )
                        
                        # upscale to fill
                        img_bg = img_bg.resize( ( resize_dimension, resize_dimension ), Image.Resampling.LANCZOS )

                        # blur bg layer
                        img_bg = img_bg.filter( ImageFilter.GaussianBlur( 20 ) )
                        
                        # paste bg to result image
                        img_result.paste(
                            img_bg,
                            (
                                ( thumb_dimension - img_bg.width ) // 2,
                                ( thumb_dimension - img_bg.height ) // 2
                            )
                        )

                        # paste thumb to result image
                        img_result.paste(
                            img_src,
                            (
                                ( thumb_dimension - img_src.width ) // 2,
                                ( thumb_dimension - img_src.height ) // 2
                            )
                        )

                        img_result.save( thumb_path, format="JPEG", optimize=True )
                        self.result.thumb = thumb_path
                except Exception as e:
                    logger.info( 'failed create thumb' )
                    traceback.print_exc()
                    pass
        logger.info( str( self.result ) )
                