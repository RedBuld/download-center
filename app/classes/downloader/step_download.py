import os
import shutil
import asyncio
import subprocess

from app import variables

from .frame import DownloaderFrame

class DownloaderStepDownload( DownloaderFrame ):

    async def Download( self ) -> None:
        try:
            shutil.rmtree( self.folders.result )
        except:
            pass
        os.makedirs( self.folders.result, exist_ok=True)

        args: list[str] = []

        args.append( '--save' )
        args.append( f'{self.folders.result}' )

        args.append( '--temp' )
        args.append( f'{self.folders.temp}' )

        args.append( '--timeout' )
        args.append( '600' )

        if self.request.url:
            args.append( '--url' )
            args.append( f'{self.request.url}' )

        if self.request.format:
            args.append( '--format' )
            if self.request.format != 'mp3':
                args.append( f'{self.request.format},json_lite' )
            else:
                args.append( 'json_lite' )
                args.append( '--additional' )
                args.append( '--additional-types' )
                args.append( 'audio' )
        else:
            raise Exception( 'Не выбран формат' )


        if self.request.cover:
            args.append( '--cover' )

        if self.request.images == False or self.request.format == 'mp3':
            args.append( '--no-image' )

        if self.request.start:
            args.append( '--start' )
            args.append( f'{self.request.start}' )

        if self.request.end:
            args.append( '--end' )
            args.append( f'{self.request.end}' )

        if self.request.login and self.request.password:
            args.append('--login')
            args.append(f'{self.request.login}')
            args.append('--password')
            args.append(f'{self.request.password}')

        if self.context.pattern:
            args.append('--book-name-pattern')
            args.append(self.context.pattern)

        if self.request.proxy:
            args.append( '--proxy' )
            args.append( f'{self.request.proxy}' )
        
        if self.context.flaresolverr:
            args.append('--flare')
            args.append(f'{self.context.flaresolverr}')

        if self.context.page_delay:
            args.append( '--delay' )
            args.append( f'{self.context.page_delay}' )

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

        self.SetStep( variables.DownloaderStep.RUNNING )

        while self.proc.returncode is None and not self.cancelled:
            message = ''
            new_line = await self.proc.stdout.readline()

            if new_line:
                message = new_line.strip().decode( self.decoder, errors='replace' )
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

        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return

        _trace = ( await self.proc.stdout.read() ).decode( 'utf-8' )
        self.dbg_log += _trace


        print('#'*20)
        print('#'*20)
        print(self.dbg_log)
        print('#'*20)
        print('#'*20)
        
        if self.proc.returncode != 0:
            error = ( await self.proc.stderr.read() ).decode( 'utf-8' )
            if error:
                raise Exception( error )
            else:
                raise ChildProcessError( 'Процесс загрузки неожиданно завершился' )
        
        files = os.listdir( self.folders.result ) if os.path.exists( self.folders.result ) else []
        if len( files ) == 0:
            error = ( await self.proc.stderr.read() ).decode( 'utf-8' )
            if error:
                raise FileExistsError( error )
            else:
                raise FileExistsError( 'Ошибка загрузки файлов' )