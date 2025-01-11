import os
import shutil
import asyncio
import subprocess
import logging
from typing import List, Dict, Any

from app import variables

from .frame import DownloaderFrame

logger = logging.getLogger('downloader-process')

class DownloaderStepDownload( DownloaderFrame ):

    async def Download( self ) -> None:
        try:
            shutil.rmtree( self.folders.result )
        except:
            pass
        os.makedirs( self.folders.result, exist_ok=True)

        args = await self.prepareDownloadArgs()

        self.PrintLog( '#'*20 )
        self.PrintLog( '#'*20 )
        self.PrintLog( ' '.join( [ os.path.join( self.context.exec_folder, self.context.downloader.folder, self.context.downloader.exec ), *args ] )  )
        self.PrintLog( '#'*20 )
        self.PrintLog( '#'*20 )

        self.proc = await asyncio.create_subprocess_exec(
            os.path.join( self.context.exec_folder, self.context.downloader.folder, self.context.downloader.exec ),
            *args,
            cwd    = os.path.join( self.context.exec_folder, self.context.downloader.folder ),
            env    = dict(os.environ),
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE
        )

        self.SetStatus( variables.DownloaderStatus.RUNNING )

        while \
            self.proc.returncode is None \
            and \
            not self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            
            message = ''
            new_line = await self.proc.stdout.readline()

            if new_line:
                message = new_line.strip().decode( 'utf-8', errors='replace' )
                self.dbg_log += '\n' + message

                if message.startswith( 'Жду ' ):
                    message = ''
                
                elif message.startswith( 'Загружена картинка' ):
                    message = ''
                
                elif message.startswith( 'Начинаю сохранение книги' ):
                    message = 'Сохраняю файлы'
                
                elif 'Дополнительный файл доступен' in message:
                    # _file = re.match(  )
                    message = 'Скачиваю доп. файл'
                
                elif 'успешно сохранена' in message:
                    message = 'Сохраняю файлы'

            if message:
                self.SetMessage( message )
            await asyncio.sleep(0.1)


        _trace = ( await self.proc.stdout.read() ).decode( 'utf-8', errors='replace' )
        self.dbg_log += _trace


        if self.__is_status__( variables.DownloaderStatus.CANCELLED ):
            return


        if self.proc.returncode != 0:
            error = ( await self.proc.stderr.read() ).decode( 'utf-8', errors='replace' )
            if error:
                self.dbg_log += error
                raise Exception( error )
            else:
                raise ChildProcessError( 'Процесс загрузки неожиданно завершился' )
        
        files = os.listdir( self.folders.result ) if os.path.exists( self.folders.result ) else []
        if len( files ) == 0:
            error = ( await self.proc.stderr.read() ).decode( 'utf-8', errors='replace' )
            if error:
                self.dbg_log += error
                raise FileExistsError( error )
            else:
                raise FileExistsError( 'Ошибка загрузки файлов' )


    async def prepareDownloadArgs( self ) -> List[ str ]:
        prepared_args: List[str] = []

        filtered_data: Dict[ str, Any ] = {}
        raw_data: Dict[ str, Any ] = {
            "result_folder": self.folders.result,
            "temp_folder": self.folders.temp,
            "url": self.request.url,
            "format": self.request.format,
            "start": self.request.start if self.request.start and self.request.start != 0 else None,
            "end": self.request.end if self.request.end and self.request.end != 0 else None,
            "login": self.request.login if self.request.login and self.request.password else None,
            "password": self.request.password if self.request.password and self.request.login else None,
            "noimages": not (self.request.images),
            "proxy": self.context.proxy,
            "flaresolverr": self.context.flaresolverr,
            "page_delay": self.context.page_delay,
        }


        source_args = self.context.downloader.args
        format_args = self.context.downloader.format_args.get( self.request.format, {} )


        for key, config in format_args.items():
            if key in source_args:
                if config.tag != None:
                    source_args[ key ].tag = config.tag
                if config.value != None:
                    source_args[ key ].value = config.value
                if config.default_value != None:
                    source_args[ key ].default_value = config.default_value
                if config.conditions:
                    source_args[ key ].conditions = config.conditions
            else:
                source_args[ key ] = config


        for key, config in source_args.items():
            if config.value or config.conditions:
                valid, value = self.validateArg( key, config, raw_data )
                if valid:
                    filtered_data[ key ] = value
            else:
                filtered_data[ key ] = True


        for key, value in filtered_data.items():
            config = source_args[ key ]
            prepared_args.append( config.tag )
            if config.value:
                mask: str = str( config.value )
                prepared_args.append( mask.replace( '{'+key+'}', str( value ) ) )

        logger.info( str( prepared_args ) )

        return prepared_args


    def validateArg( self, key: str, config: variables.DownloaderConfigArg, data: Dict[ str, Any ] ) -> tuple[ bool, Any ]:

        value = data.get( key, None )

        if not value:
            if config.default_value:
                value = config.default_value

        valid = True
        for condition in config.conditions:
            ct = type( condition )
            if ct == str and condition == 'nonempty':
                if value == None or value == '':
                    valid = False
            elif ct == str and condition == 'nonzero':
                if value == 0:
                    valid = False
            elif ct == str and condition == 'nonnull':
                if value == None:
                    valid = False
            elif ct == bool:
                if value != condition:
                    valid = False
        
        return valid, value