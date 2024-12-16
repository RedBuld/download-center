from __future__ import annotations

import signal
import os
import re
import sys
import asyncio
import ujson
import logging
import traceback
import shutil
import subprocess
from multiprocessing import Queue
from typing import Dict, List, Any
from app import dto
from app import variables

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

class Downloader():
    request:  dto.DownloadRequest
    context:  variables.DownloaderContext
    statuses: Queue
    results:  Queue
    proc:     asyncio.subprocess.Process
    temp:     variables.DownloaderTemp

    done:      bool = False
    cancelled: bool = False

    step:      int = variables.DownloaderStep.IDLE
    prev_step: int = variables.DownloaderStep.IDLE
    
    message:      str = ''
    prev_message: str = ''

    dbg_log:    str = ''
    dbg_config: str = ''

    results_folder:  str = ''
    temp_folder:     str = ''
    archives_folder: str = ''

    decoder    = 'utf-8'
    file_limit = 1_549_000_000
    
    def __debug_config__( self ) -> str:
        return ujson.dumps( {
            'request': self.request.__export__(),
            'context': self.context.__export__(),
            'temp':    self.temp.__export__(),
        }, indent=4, ensure_ascii=False )

    def __repr__( self ) -> str:
        return str( {
            'request':         self.request,
            'context':         self.context,
            'proc':            self.proc,
            'temp':            self.temp,
            'done':            self.done,
            'cancelled':       self.cancelled,
            'step':            self.step,
            'prev_step':       self.prev_step,
            'message':         self.message,
            'prev_message':    self.prev_message,
            'results_folder':  self.results_folder,
            'temp_folder':     self.temp_folder,
            'archives_folder': self.archives_folder
        } )

    def __init__(
        self,
        request:  dto.DownloadRequest,
        context:  variables.DownloaderContext = None,
        statuses: Queue = None,
        results:  Queue = None,
    ) -> None:
        self.request   = request
        self.context   = context
        self.statuses  = statuses
        self.results   = results
        
        self.done       = False
        self.cancelled  = False

        self.step         = variables.DownloaderStep.IDLE
        self.prev_step    = variables.DownloaderStep.IDLE

        self.message      = ''
        self.prev_message = ''

        self.dbg_log    = ''
        self.dbg_config = ''

        self.results_folder = os.path.join( self.context.save_folder, str( self.request.task_id ) )
        self.temp_folder    = os.path.join( self.context.temp_folder, str( self.request.task_id ) )

        self.proc = None
        self.temp = variables.DownloaderTemp()

        self.decoder    = 'utf-8'
        self.file_limit = 1_549_000_000

        signal.signal( signal.SIGINT, self.CancelDownload )
        signal.signal( signal.SIGTERM, self.CancelDownload )

    def __is_step__(
        self,
        check_step: int
    ) -> bool:
        return self.step == check_step

    ###

    def StartDownload( self ) -> None:
        # 
        logging.basicConfig(
            format='%(levelname)s: %(name)s[%(process)d] %(asctime)s - %(message)s',
            level=logging.INFO
        )
        logger.info( 'Downloader: Start' )
        self.SetStep( variables.DownloaderStep.WAIT )
        self.SetMessage( 'Загрузка начата' )
        asyncio.get_event_loop().run_until_complete( self.Run() )


    def CancelDownload( self, *args, **kwargs ):
        self.cancelled = True
        
    ###

    async def Run( self ) -> None:
        asyncio.create_task( self.statusRunner() )
        await asyncio.sleep( 0 )

        self.SetStep( variables.DownloaderStep.INIT )

        try:
            await self.DownloadStep() # can raise error
            await self.ProcessStep() # can't raise error
        except Exception as e:
            traceback.print_exc()
            self.done = True
            await self.ProcessError( e )
        finally:
            self.done = True
            await self.SendResult()


    def Stop( self ) -> None:
        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return

        logger.info( 'Downloader: stop' )

        self.done = True

        self.SetStep( variables.DownloaderStep.CANCELLED )
        self.SetMessage( 'Загрузка отменена' )
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()

    #

    async def statusRunner( self ) -> None:
        while not self.done:
            await self.SendStatus()
            await asyncio.sleep(5)

    #

    def ProcessHashtags(
        self,
        raw_hashtags: List[ str ] = []
    ) -> List[ str ]:
        selected_hashtags = self.request.hashtags

        if selected_hashtags == 'bf':
            return self.ProcessHashtags_bf( raw_hashtags )
        elif selected_hashtags == 'gf':
            return self.ProcessHashtags_gf( raw_hashtags )
        else:
            return []


    def ProcessHashtags_bf(
        self,
        raw_hashtags: List[ str ] = []
    ) -> List[ str ]:
        hashtags = []
        for hashtag in raw_hashtags:
            hashtag = re.sub( r'[^A-Za-z0-9А-Яа-яёЁ]', ' ', hashtag )
            hashtag = re.sub( r'\s+', '_', hashtag.strip() )
            hashtags.append( f'#{hashtag}' )
        return hashtags


    def ProcessHashtags_gf(
        self,
        raw_hashtags: List[ str ] = []
    ) -> List[ str ]:
        hashtags = []
        for hashtag in raw_hashtags:
            hashtag = re.sub( r'[^A-Za-z0-9А-Яа-яёЁ]', '', hashtag ).lower()
            hashtags.append( f'#{hashtag}' )
        return hashtags


    def PrepareChapters( self ) -> str:
        _return = self.temp.last_chapter_name
        suffix = ''
        
        _total = self.temp.chapters_total
        _valid = self.temp.chapters_valid

        if self.temp.chapters_valid < self.temp.chapters_total:
            _total = self.temp.chapters_valid

        if _valid > 1:
            _return = f'По: "{_return}"'

        if _total > 0:
            _start = int(self.request.start)
            _end = int(self.request.end)

            if _start != 0 and _end != 0:
                suffix = f'{_start} - {_end}'
            elif _start != 0 and _end == 0:
                if _start > 0:
                    _end = _start + _total
                    suffix = f'{_start} - {_end}'
            # else:
            #     suffix = f'1 - {_total}'
        
        if self.temp.chapters_valid < self.temp.chapters_total:
            if suffix:
                suffix += f' / {self.temp.chapters_total}'
            else:
                suffix += f'{_total} / {self.temp.chapters_total}'

        if suffix:
            suffix = f' [{suffix}]'

        # if self.temp.first_chapter_name and self.temp.last_chapter_name:
        #     if self.request.start or self.request.end:
        #         chapters = f'Глав {self.temp.chapters_valid} из {self.temp.chapters_total}, с "{self.temp.first_chapter_name}" по "{self.temp.last_chapter_name}"'
        #     else:
        #         chapters = f'Глав {self.temp.chapters_valid} из {self.temp.chapters_total}, по "{self.temp.last_chapter_name}"'
        # else:
        #     chapters = f'Глав {self.temp.chapters_valid} из {self.temp.chapters_total}'

        return f'{_return}{suffix}'


    def EscapeErrorText(
        self,
        text: str
    ) -> str:
        text = text.translate(
            str.maketrans(
                {
                    '<': '&lt;',
                    '>': '&rt;',
                    '&': '&amp;',
                    '\'': '&quot;',
                    '\"': '&quot;',
                }
            )
        )
        return text


    async def ProcessError(
        self,
        err: Exception
    ) -> None:
    
        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return

        self.SetStep( variables.DownloaderStep.ERROR )

        self.temp.text = 'Произошла ошибка: '

        if 'с ошибкой' in self.dbg_log:
            if 'Получен бан. Попробуйте позже' in self.dbg_log:
                self.temp.text += 'Получен бан. Попробуйте позже.'
        else:
            self.temp.text += '\n<pre>\n'+ self.EscapeErrorText( str( err ) )[ :2000 ] +'\n</pre>'


    def SetStep(
        self,
        new_step: int
    ) -> None:
        self.prev_step = self.step
        self.step = new_step


    def SetMessage(
        self,
        new_message: str
    ) -> None:
        self.prev_message = self.message
        self.message = new_message


    async def DownloadStep( self ) -> None:
        try:
            shutil.rmtree( self.results_folder )
        except:
            pass
        os.makedirs(self.results_folder, exist_ok=True)

        args: list[str] = []

        args.append( '--save' )
        args.append( f'{self.results_folder}' )

        args.append( '--temp' )
        args.append( f'{self.temp_folder}' )

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

        logger.info('#'*20)
        logger.info('#'*20)
        logger.info(' '.join( [ os.path.join( self.context.exec_folder, self.context.downloader.folder, self.context.downloader.exec ), *args ] ) )
        logger.info('#'*20)
        logger.info('#'*20)

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
        
        if self.cancelled:
            self.Stop()

        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return

        _trace = ( await self.proc.stdout.read() ).decode( 'utf-8' )
        self.dbg_log += _trace
        
        if self.proc.returncode != 0:
            error = ( await self.proc.stderr.read() ).decode( 'utf-8' )
            if error:
                raise Exception( error )
            else:
                raise ChildProcessError( 'Процесс загрузки неожиданно завершился' )
        
        files = os.listdir( self.results_folder ) if os.path.exists( self.results_folder ) else []
        if len( files ) == 0:
            error += ( await self.proc.stderr.read() ).decode( 'utf-8' )
            if error:
                raise FileExistsError( error )
            else:
                raise FileExistsError( 'Ошибка загрузки файлов' )


    async def ProcessStep( self ) -> None:

        if self.cancelled:
            return self.Stop()

        self.SetStep( variables.DownloaderStep.PROCESSING )
        self.SetMessage( 'Обработка файлов' )

        await self.CheckFiles()

        if self.cancelled:
            return self.Stop()

        await self.RenameFiles()

        if self.cancelled:
            return self.Stop()

        await self.ProcessFiles()

        if self.cancelled:
            return self.Stop()

        self.SetStep( variables.DownloaderStep.DONE )
        self.SetMessage( 'Выгрузка файлов' )


    async def CheckFiles( self ) -> None:
        trash = []
        root_files = os.listdir( self.results_folder )

        for file in root_files:
            file_path = os.path.join( self.results_folder, file )
    
            if os.path.isdir( file_path ):

                audio_folder = os.path.join( file_path, 'Audio' )
                if os.path.isdir( audio_folder ):
                    audio_folder_files = os.listdir( audio_folder )
                    for file in audio_folder_files:
                        file_path = os.path.join( audio_folder, file )

                        file_name, extension = os.path.splitext( file )
                        extension = extension[1:]
                        
                        if extension == self.request.format and not file_name.startswith( 'sample' ):
                            self.temp.source_files.append( file_path )
                        else:
                            trash.append( file_path )

            else:
                file_name, extension = os.path.splitext( file )
                extension = extension[1:]

                if extension == 'json':
                    self.temp.text = await self.ProcessCaption( file_path )
                    trash.append( file_path )

                elif extension == self.request.format:
                    self.temp.source_files.append( file_path )

                elif extension in [ 'jpg','jpeg','png','gif' ] and file_name.endswith( '_cover' ):
                    self.temp.cover = file_path

                else:
                    trash.append( file_path )

        for file in trash:
            os.remove( file )


    async def RenameFiles( self ) -> None:
        source_files = []
        index = 1
        need_index = len( self.temp.source_files ) > 1

        suffix = ''
        if self.request.format != 'mp3':
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
                for file in self.temp.source_files:
                    original_file = file

                    path, file = os.path.split( original_file )
                    old_name, extension = os.path.splitext( file )

                    new_name = old_name + suffix + (f" ({index})" if need_index else '') + extension
                    new_file = os.path.join( path, new_name )

                    os.rename( original_file, new_file )

                    source_files.append( new_file )
                    index += 1
            else:
                source_files = self.temp.source_files
        
        else:
            index = 1
            need_index = len( self.temp.source_files ) > 1
            for file in self.temp.source_files:
                original_file = file

                path, file = os.path.split( original_file )
                old_name, extension = os.path.splitext( file )

                new_name = f"{self.temp.author} - {self.temp.name}" + (f" ({index})" if need_index else '') + extension
                new_file = os.path.join( path, new_name )

                os.rename( original_file, new_file )

                source_files.append( new_file )
                index += 1

        self.temp.source_files = source_files


    async def ProcessFiles( self ) -> None:

        orig_size = 0
        result_files = []
        archives_folder = ''

        preselected_archiver = None
        for key, executable in self.context.compression.items():
            if os.path.exists( executable[ 'bin' ] ):
                preselected_archiver = key

        if len( self.temp.source_files ) > 0:
            for file in self.temp.source_files:
                original_file = file

                size = os.path.getsize( original_file )
                orig_size += size

                if size < self.file_limit:
                    result_files.append( original_file )
                else:
                    file = os.path.basename( original_file )
                    file_name, _ = os.path.splitext( file )

                    self.SetMessage( f'Архивация файла {file_name}' )

                    archives_folder = os.path.join( self.context.arch_folder, str(self.request.task_id) )
                    os.makedirs( archives_folder, exist_ok=True )

                    target_archive = os.path.join( archives_folder, f'{file_name}' )

                    if preselected_archiver:
                        split_file_size = int(self.file_limit / 1000 / 1000)
                        split_file_size = f'{split_file_size}m'

                        if preselected_archiver == 'zip':
                            args = [f'-s{split_file_size}', '-0', target_archive, original_file]

                        elif preselected_archiver == 'rar':
                            args = [ 'a' , f'-v{split_file_size}', '-ep', '-m0', target_archive, original_file]

                        elif preselected_archiver == '7z':
                            args = [ 'a' , f'-v{split_file_size}', '-mx0', target_archive, original_file]

                        self.proc = await asyncio.create_subprocess_exec(
                            self.context.compression[ preselected_archiver ][ 'bin' ],
                            *args,
                            cwd    = self.context.compression[ preselected_archiver ][ 'cwd' ],
                            env    = dict(os.environ),
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE
                        )
                        await self.proc.wait()

                        if self.proc.returncode == 0:
                            try:
                                os.remove( file )
                            except:
                                pass
                        else:
                            error = await self.proc.stdout.read()
                            error += await self.proc.stderr.read()
                            if error:
                                raise Exception( error.decode('utf-8') )
                            else:
                                raise ProcessLookupError('Process closed unexpectedly')

        if archives_folder:
            t = os.listdir(archives_folder)
            for x in t:
                parted = os.path.join( archives_folder, x )
                result_files.append( parted )
                self.temp.oper_size += os.path.getsize( parted )

        if len(result_files) > 0:
            self.temp.result_files = result_files
        self.temp.source_files = None
        self.temp.orig_size = orig_size

        # print('ProcessFiles',self.temp.result_files)
    
    async def ProcessCaption(
        self,
        filepath: str
    ) -> str:

        book_title: str = ''
        book_url: str = ''
        seria_name: str = ''
        seria_url: str = ''
        authors: List[ str ] = []
        chapters: str = ''

        hashtags: List[ str ] = []

        with open(filepath, "r") as f:
            _raw: str = f.read()
            try:
                _json: Dict[ str, Any ] = ujson.loads(_raw)
            except:
                return ''

            if 'Title' in _json and _json[ 'Title' ]:
                book_title = _json[ 'Title' ]
                self.temp.name = _json[ 'Title' ]

            if 'Url' in _json and _json[ 'Url' ]:
                book_url = _json[ 'Url' ]

            if 'Author' in _json:
                if 'Name' in _json[ 'Author' ]:
                    _a_name: str = _json[ 'Author' ][ 'Name' ]
                    _a_name = _a_name.replace( '\n', ' ' )
                    self.temp.author = _a_name
                    hashtags.append(_a_name)

                    if 'Url' in _json[ 'Author' ]:
                        _a_url: str = _json[ 'Author' ][ 'Url' ]
                        authors.append( f'<a href="{_a_url}">{_a_name}</a>' )
                    else:
                        authors.append( _a_name )
                    

            if 'CoAuthors' in _json and _json[ 'CoAuthors' ]:
                for _author in _json[ 'CoAuthors' ]:
                    if 'Name' in _author:
                        _c_name: str = _author[ 'Name' ]
                        _c_name = _c_name.replace( '\n',' ' )
                        hashtags.append(_c_name)

                        if 'Url' in _author:
                            _c_url: str = _author[ 'Url' ]
                            authors.append( f'<a href="{_c_url}">{_c_name}</a>' )
                        else:
                            authors.append( _c_name )

            if 'Seria' in _json and _json[ 'Seria' ]:
                if 'Name' in _json[ 'Seria' ]:
                    seria_name: str = _json[ 'Seria' ][ 'Name' ]
                    seria_name = seria_name.replace( '\n', ' ' )
                    seria_name = re.sub( r'\s+', ' ', seria_name )
                    hashtags.append(seria_name)

                    if 'Number' in _json[ 'Seria' ]:
                        seria_name += ' #' + str(_json[ 'Seria' ][ 'Number' ])

                    if 'Url' in _json[ 'Seria' ]:
                        seria_url = _json[ 'Seria' ][ 'Url' ]

            if 'Chapters' in _json and _json[ 'Chapters' ]:
                if len( _json[ 'Chapters' ] ) > 0:
                    for chapter in _json[ 'Chapters' ]:
                        if chapter[ 'Title' ]:
                            self.temp.chapters_total += 1
                            if chapter[ 'IsValid' ]:
                                self.temp.chapters_valid += 1
                                _c_name: str = chapter[ 'Title' ]
                                _c_name = _c_name.replace('\n',' ')
                                if not self.temp.first_chapter_name:
                                    self.temp.first_chapter_name = _c_name
                                self.temp.last_chapter_name = _c_name


        result = ''
        if book_title and book_url:
            result += f'<a href="{book_url}">{book_title}</a>\n'
        elif book_title:
            result += f'{book_title}\n'
        
        if len(authors) > 0:
            _authors: str = ', '.join( authors )
            if len(authors) > 1:
                result += f'Авторы: {_authors}\n'
            else:
                result += f'Автор: {_authors}\n'

        self.temp.last_chapter_name = re.sub( r'\s+', ' ', self.temp.last_chapter_name )
        self.temp.last_chapter_name = self.temp.last_chapter_name[:200]
        
        if seria_name and seria_url:
            result += f'Серия: <a href="{seria_url}">{seria_name}</a>\n'
        elif seria_name:
            result += f'Серия: {seria_name}\n'
        
        chapters = self.PrepareChapters()

        if chapters:
            result += "\n"
            result += f'{chapters}'

        _hashtags = self.ProcessHashtags( hashtags )
        
        if _hashtags:
            result += "\n"
            result += "\n"
            result += ' '.join( _hashtags )

        return result

    # external data transfer

    async def SendStatus( self ) -> None:

        if self.message == self.prev_message:
            return

        self.SetMessage( self.message )

        status = dto.DownloadStatus(
            task_id =    self.request.task_id,
            user_id =    self.request.user_id,
            bot_id =     self.request.bot_id,
            web_id =     self.request.web_id,
            chat_id =    self.request.chat_id,
            message_id = self.request.message_id,
            text =       self.message,
            status =     self.step,
        )

        self.statuses.put( status.model_dump() )


    async def SendResult( self ) -> None:

        if self.temp_folder and os.path.exists( self.temp_folder ):
            try:
                shutil.rmtree( self.temp_folder )
            except:
                pass

        if self.__is_step__( variables.DownloaderStep.ERROR ) or self.__is_step__( variables.DownloaderStep.CANCELLED ):
            self.temp.cover = ''
            self.temp.result_files = []
            if self.results_folder and os.path.exists( self.temp_folder ):
                try:
                    shutil.rmtree( self.results_folder )
                except:
                    pass

        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return
        
        if not self.__is_step__( variables.DownloaderStep.ERROR ):
            self.dbg_log = None
        else:
            self.dbg_config = self.__debug_config__()
        
        result = dto.DownloadResult(
            task_id    = self.request.task_id,
            user_id    = self.request.user_id,
            bot_id     = self.request.bot_id,
            web_id     = self.request.web_id,
            chat_id    = self.request.chat_id,
            message_id = self.request.message_id,
            status     = self.step,
            site       = self.request.site,
            text       = self.temp.text,
            cover      = self.temp.cover,
            files      = self.temp.result_files,
            orig_size  = self.temp.orig_size,
            oper_size  = self.temp.oper_size,
            folder     = self.results_folder,
            proxy      = self.request.proxy,
            url        = self.request.url,
            format     = self.request.format,
            start      = self.request.start,
            end        = self.request.end,
            dbg_log    = self.dbg_log,
            dbg_config = self.dbg_config
        )

        self.results.put( result.model_dump() )

        sys.exit(0)