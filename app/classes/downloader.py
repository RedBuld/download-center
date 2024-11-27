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
from app import models
from app import schemas
from app import variables

logger = logging.getLogger('downloader-process')

def start_downloader(
        request:      models.DownloadRequest,
        context:      variables.DownloaderContext = None,
        statuses:     Queue = None,
        results:      Queue = None
    ):
    _downloader = Downloader(
        request =      request,
        context =      context,
        statuses =     statuses,
        results =      results
    )
    _downloader.Start()

class Downloader():
    request:      models.DownloadRequest
    context:      variables.DownloaderContext = None,
    cancelled:    bool = False
    statuses:     Queue = None
    results:      Queue = None

    done: bool = False

    step: int = variables.DownloaderStep.IDLE
    prev_step: int = variables.DownloaderStep.IDLE
    
    message: str = ""
    prev_message: str = ""

    proc: asyncio.subprocess.Process
    temp: variables.DownloaderTemp

    _folder: str = ""
    _temp: str = ""
    
    def __repr__(self) -> str:
        return str({
            'cancelled': self.cancelled,
            'request': self.request,
            'context':  self.context,
            'step': self.step,
            'prev_step': self.prev_step,
            'message': self.message,
            'prev_message': self.prev_message,
            'proc': self.proc,
            'temp': self.temp
        })

    def __init__( self,
        request:      models.DownloadRequest,
        context:      variables.DownloaderContext = None,
        statuses:     Queue = None,
        results:      Queue = None,
    ):
        self.request =   request
        self.context =   context
        self.statuses =  statuses
        self.results =   results
        self.cancelled = False
        self.__reset()

        signal.signal(signal.SIGINT, self.on_cancel)
        signal.signal(signal.SIGTERM, self.on_cancel)

    def __is_step__(self, check_step: int) -> bool:
        return self.step == check_step

    def on_cancel( self, *args, **kwargs ):
        self.cancelled = True
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()

    def __reset(self) -> None:
        self.step = variables.DownloaderStep.IDLE
        self.prev_step = variables.DownloaderStep.IDLE
        self.message = ""
        self.prev_message = ""

        self._folder = os.path.join( self.context.save_folder, str(self.request.task_id) )
        self._temp = os.path.join( self.context.temp_folder, str(self.request.task_id) )

        self.proc = None
        self.temp = variables.DownloaderTemp()

        self.done = False
        self.decoder = 'utf-8'
        self.file_limit = 249_000_000

    def __prepare_hashtags( self, raw_hashtags: List[str] = [] ) -> List[str]:
        htm = self.request.hashtags
        if htm == 'bf':
            return self.__prepare_hashtags_bf(raw_hashtags)
        elif htm == 'gf':
            return self.__prepare_hashtags_gf(raw_hashtags)
        else:
            return []

    def __prepare_hashtags_bf( self, raw_hashtags: List[str] = [] ) -> List[str]:
        hashtags = []
        for hashtag in raw_hashtags:
            hashtag = re.sub(r'[^A-Za-z0-9А-Яа-яёЁ]', ' ', hashtag)
            hashtag = re.sub(r'\s+', '_', hashtag.strip())
            hashtags.append( f'#{hashtag}' )
        return hashtags

    def __prepare_hashtags_gf( self, raw_hashtags: List[str] = [] ) -> List[str]:
        hashtags = []
        for hashtag in raw_hashtags:
            hashtag = re.sub(r'[^A-Za-z0-9А-Яа-яёЁ]', '', hashtag).lower()
            hashtags.append( f'#{hashtag}' )
        return hashtags

    def __escape_err( self, text: str ) -> str:
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


    def __set_step(self, new_step: int) -> None:
        self.prev_step = self.step
        self.step = new_step


    def __set_message(self, new_message: str) -> None:
        self.prev_message = self.message
        self.message = new_message

    ###

    def Start(self) -> None:
        self.__reset()
        # 
        logging.basicConfig(
            format='\x1b[32m%(levelname)s\x1b[0m:     %(name)s[%(process)d] %(asctime)s - %(message)s',
            level=logging.INFO
        )
        logger.info('Downloader: Start')
        self.__set_step(variables.DownloaderStep.WAIT)
        self.__set_message('Загрузка начата')
        asyncio.get_event_loop().run_until_complete( self.start() )


    def Stop(self) -> None:
        if self.__is_step__(variables.DownloaderStep.CANCELLED):
            return

        self.done = True

        logger.info('Downloader: Stop')
        self.__set_step(variables.DownloaderStep.CANCELLED)
        self.__set_message('Загрузка отменена')
        if self.proc and self.proc.returncode is None:
            self.proc.terminate()
        
    ###

    async def start(self) -> None:
        asyncio.create_task( self.__status_runner() )
        await asyncio.sleep(0)

        self.__set_step(variables.DownloaderStep.INIT)

        try:
            await self.download() # can raise error
            await self.process() # can't raise error
        except Exception as e:
            traceback.print_exc()
            self.done = True
            await self.__error(e)
        finally:
            self.done = True
            await self.__result()

    async def __status_runner(self) -> None:
        while not self.done:
            await self.__status()
            await asyncio.sleep(5)

    async def download(self) -> None:
        try:
            shutil.rmtree( self._folder )
        except:
            pass
        os.makedirs(self._folder, exist_ok=True)

        args: list[str] = []

        args.append('--save')
        args.append(f'{self._folder}')

        args.append('--temp')
        args.append(f'{self._temp}')

        if self.request.url:
            args.append('--url')
            args.append(f'{self.request.url}')

        if self.request.format:
            args.append('--format')
            if self.request.format != 'mp3':
                args.append(f'{self.request.format},json_lite')
            else:
                args.append('json_lite')
                args.append('--additional')
                args.append('--additional-types')
                args.append('audio')
        else:
            args.append('--format')
            args.append(f'fb2,json_lite')

        if self.request.proxy:
            args.append('--proxy')
            args.append(f'{self.request.proxy}')
            args.append('--timeout')
            args.append('1200')
        else:
            args.append('--timeout')
            args.append('600')

        if self.context.page_delay:
            args.append('--delay')
            args.append(f'{self.context.page_delay}')

        if self.request.cover:
            args.append('--cover')

        if self.request.images == False or self.request.format == 'mp3':
            args.append('--no-image')

        if self.request.start:
            args.append('--start')
            args.append(f'{self.request.start}')

        if self.request.end:
            args.append('--end')
            args.append(f'{self.request.end}')

        if self.request.login and self.request.password:

            if  not self.request.login.startswith('/') and not self.request.login.startswith('http:/') and not self.request.login.startswith('https:/')\
                and\
                not self.request.password.startswith('/') and not self.request.password.startswith('http:/') and not self.request.password.startswith('https:/'):
                args.append('--login')
                args.append(f'{self.request.login}')
                args.append('--password')
                args.append(f'{self.request.password}')

        logger.info('#'*20)
        logger.info('#'*20)
        logger.info(' '.join([os.path.join(self.context.exec_folder, self.context.downloader.folder, self.context.downloader.exec), *args]) )
        logger.info('#'*20)
        logger.info('#'*20)

        self.proc = await asyncio.create_subprocess_exec(
            os.path.join(self.context.exec_folder, self.context.downloader.folder, self.context.downloader.exec),
            *args,
            cwd=os.path.join(self.context.exec_folder, self.context.downloader.folder),
            env=os.environ,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.__set_step(variables.DownloaderStep.RUNNING)

        message = ''
        
        while self.proc.returncode is None and not self.cancelled:
            _msg = ''
            new_line = await self.proc.stdout.readline()
            if new_line:
                _msg = new_line.strip().decode(self.decoder, errors='replace')
                if _msg.startswith('Жду '):
                    _msg = ''
                if _msg.startswith('Загружена картинка'):
                    _msg = ''
                elif _msg.startswith('Начинаю сохранение книги'):
                    _msg = 'Сохраняю файлы'
                elif 'Дополнительный файл доступен' in _msg:
                    _msg = 'Скачиваю доп. файл'
                elif 'успешно сохранена' in _msg:
                    _msg = 'Сохраняю файлы'
            if _msg:
                message = _msg
                self.__set_message(_msg)
            await asyncio.sleep(0.1)
        
        if self.cancelled:
            return self.Stop()

        if self.__is_step__(variables.DownloaderStep.CANCELLED):
            return
        
        if self.proc.returncode != 0:
            error = await self.proc.stderr.read()
            if error:
                raise Exception(error.decode('utf-8'))
            else:
                raise ProcessLookupError('Process closed unexpectedly')
        
        t = os.listdir(self._folder)
        if len(t) == 0:
            error = ( await self.proc.stdout.read() ).decode('utf-8')
            error += ( await self.proc.stderr.read() ).decode('utf-8')
            if 'с ошибкой' in message and error:
                if 'Получен бан. Попробуйте позже' in message:
                    raise Exception('Получен бан. Попробуйте позже.')
                else:
                    raise Exception(message + '\n' + error)
            else:
                raise FileExistsError('Ощибка загрузки файлов')
    
    async def process(self) -> None:

        if self.cancelled:
            return self.Stop()

        self.__set_step(variables.DownloaderStep.PROCESSING)
        self.__set_message('Обработка файлов')

        await self.check_files()

        if self.cancelled:
            return self.Stop()

        await self.rename_files()

        if self.cancelled:
            return self.Stop()

        await self.process_files()

        if self.cancelled:
            return self.Stop()

        self.__set_step(variables.DownloaderStep.DONE)
        self.__set_message('Выгрузка файлов')

    async def check_files(self) -> None:

        trash = []
        
        paths = os.listdir(self._folder)
        # print('check_files')
        # print(self._folder)
        # print(paths)
        for path in paths:
            if os.path.isdir(os.path.join(self._folder, path)):
                _audio = os.path.join(self._folder, path, 'Audio')
                if os.path.isdir(_audio):
                    audios = os.listdir(_audio)
                    for track in audios:
                        fname, extension = os.path.splitext(track)
                        extension = extension[1:]
                        if extension == self.request.format and not fname.startswith('sample'):
                            self.temp.source_files.append( os.path.join(_audio, track) )
            else:
                fname, extension = os.path.splitext(path)
                extension = extension[1:]

                if extension == 'json':
                    _json = os.path.join(self._folder, path)
                    self.temp.text = await self.process_caption( _json )
                    trash.append( _json )

                elif extension == self.request.format:
                    self.temp.source_files.append( os.path.join(self._folder, path) )

                elif extension in ['jpg','jpeg','png','gif'] and fname.endswith('_cover'):
                    self.temp.cover = os.path.join(self._folder, path)

                else:
                    trash.append( os.path.join(self._folder, path) )

        for file in trash:
            os.remove(file)
    
    async def rename_files(self) -> None:
        source_files = []
        index = 1
        need_index = len(self.temp.source_files) > 1

        # print('rename_files',self.temp.source_files)

        suffix = ''
        if self.request.format != 'mp3':
            if self.request.start or self.request.end:
                _chapters = self.temp.chapters
                if _chapters > 0:
                    _start = self.request.start
                    _end = self.request.end

                    if _start and _end:
                        _start = int(_start)
                        _end = int(_end)
                        if _start > 0 and _end > 0:
                            suffix = f'-parted-from-{_start}-to-{_end}'
                        elif _start > 0 and _end < 0:
                            __end = _start+_chapters
                            suffix = f'-parted-from-{_start}-wo-last-{__end}'
                    elif _start and not _end:
                        _start = int(_start)
                        if _start > 0:
                            __end = _start+_chapters
                            suffix = f'-parted-from-{_start}-to-{__end}'
                        else:
                            if abs(_start) >= _chapters:
                                suffix = f'-parted-last-{_start}'
                    elif _end and not _start:
                        _end = int(_end)
                        if _end > 0:
                            suffix = f'-parted-from-1-to-{_chapters}'
                        else:
                            _end = abs(_end)
                            if _end >= _chapters:
                                suffix = f'-parted-from-1-to-{_chapters}'
                            else:
                                suffix = f'-parted-wo-last-{_end}'

            if suffix != '':
                for file in self.temp.source_files:
                    original_file = file

                    path, file = os.path.split(original_file)
                    old_name, extension = os.path.splitext(file)

                    new_name = old_name + suffix + (f" ({index})" if need_index else "") + extension
                    new_file = os.path.join(path, new_name)

                    os.rename(original_file, new_file)

                    source_files.append(new_file)
                    index += 1
            else:
                source_files = self.temp.source_files
        
        else:
            index = 1
            need_index = len(self.temp.source_files) > 1
            for file in self.temp.source_files:
                original_file = file

                path, file = os.path.split(original_file)
                old_name, extension = os.path.splitext(file)

                new_name = f"{self.temp.author} - {self.temp.name}" + (f" ({index})" if need_index else "") + extension
                new_file = os.path.join(path, new_name)

                os.rename(original_file, new_file)

                source_files.append(new_file)
                index += 1

        self.temp.source_files = source_files

    async def process_files(self) -> None:

        orig_size = 0
        result_files = []
        splitted_folder = ""

        # print('process_files',self.temp.source_files)

        preselected_archiver = None
        for key, executable in self.context.compression.items():
            if os.path.exists( executable ):
                preselected_archiver = key

        if len(self.temp.source_files) > 0:
            for file in self.temp.source_files:
                original_file = file

                size = os.path.getsize(original_file)
                orig_size += size

                if size < self.file_limit:
                    result_files.append(original_file)
                else:
                    self.__set_message('Архивация файлов')

                    file = os.path.basename(original_file)
                    file_name, _ = os.path.splitext(file)

                    splitted_folder = os.path.join(self._folder, 'splitted')
                    os.makedirs(splitted_folder, exist_ok=True)

                    target_archive = os.path.join(splitted_folder, f'{file_name}')

                    if preselected_archiver:
                        if preselected_archiver == 'zip':
                            sfs = int(self.file_limit / 1000 / 1000)
                            _sfs = f'{sfs}m'
                            args = [f'-s{_sfs}', '-0', target_archive, original_file]
                        if preselected_archiver == 'winrar':
                            sfs = int(self.file_limit / 1000 / 1000)
                            _sfs = f'{sfs}m'
                            args = ['a', '-afzip', f'-v{_sfs}', '-ep', '-m0', target_archive, original_file]
                        if preselected_archiver == 'rar':
                            sfs = int(self.file_limit / 1000 / 1000)
                            _sfs = f'{sfs}m'
                            args = ['a', f'-v{_sfs}', '-ep', '-m0', target_archive, original_file]
                        if preselected_archiver == '7z':
                            sfs = int(self.file_limit / 1000 / 1000)
                            _sfs = f'{sfs}m'
                            args = ['a', f'-v{_sfs}', '-mx0', target_archive, original_file]

                        self.proc = await asyncio.create_subprocess_exec(
                            executable,
                            *args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        await self.proc.wait()

                        if self.proc.returncode == 0:
                            try:
                                os.unlink(file)
                            except:
                                pass

        if splitted_folder:
            t = os.listdir(splitted_folder)
            for x in t:
                parted = os.path.join( splitted_folder, x )
                result_files.append( parted )
                self.temp.oper_size += os.path.getsize( parted )

        if len(result_files) > 0:
            self.temp.result_files = result_files
        self.temp.source_files = None
        self.temp.orig_size = orig_size

        # print('process_files',self.temp.result_files)
    
    async def process_caption(self, filepath: str) -> str:
        book_title: str = ""
        book_url: str = ""
        seria_name: str = ""
        seria_url: str = ""
        authors: list[str] = []
        chapters: str = ""

        hashtags: list[str] = []

        with open(filepath, "r") as f:
            _raw: str = f.read()
            try:
                _json: Dict[str, Any] = ujson.loads(_raw)
            except:
                return ''

            if 'Title' in _json and _json['Title']:
                book_title = _json['Title']
                self.temp.name = _json['Title']

            if 'Url' in _json and _json['Url']:
                book_url = _json['Url']

            if 'Author' in _json:
                if 'Name' in _json['Author']:
                    _a_name: str = _json['Author']['Name'].replace('\n',' ')
                    hashtags.append(_a_name)
                    if 'Url' in _json['Author']:
                        _a_url: str = _json['Author']['Url']
                        authors.append( f'<a href="{_a_url}">{_a_name}</a>' )
                    else:
                        authors.append( _a_name )
                    
                    self.temp.author = _a_name

            if 'CoAuthors' in _json and _json['CoAuthors']:
                for _author in _json['CoAuthors']:
                    if 'Name' in _author:
                        _c_name: str = _author['Name'].replace('\n',' ')
                        hashtags.append(_c_name)
                        if 'Url' in _author:
                            _c_url: str = _author['Url']
                            authors.append( f'<a href="{_c_url}">{_c_name}</a>' )
                        else:
                            authors.append( _c_name )

            if 'Seria' in _json and _json['Seria']:
                if 'Name' in _json['Seria']:
                    seria_name = _json['Seria']['Name'].replace('\n',' ')
                    hashtags.append(seria_name)
                    if 'Number' in _json['Seria']:
                        seria_name += ' #' + str(_json['Seria']['Number'])
                    if 'Url' in _json['Seria']:
                        seria_url = _json['Seria']['Url']

            if 'Chapters' in _json and _json['Chapters']:
                total_chapters: int = 0
                valid_chapters: int = 0
                first_chapter: str = ''
                last_chapter: str = ''
                if len(_json['Chapters']) > 0:
                    for chapter in _json['Chapters']:
                        if chapter['Title']:
                            total_chapters += 1
                            if chapter['IsValid']:
                                valid_chapters += 1
                                _c_name = chapter['Title'].replace('\n',' ')
                                if not first_chapter:
                                    first_chapter = _c_name
                                last_chapter = _c_name
                    if first_chapter and last_chapter:
                        if self.request.start or self.request.end:
                            chapters = f'Глав {valid_chapters} из {total_chapters}, с "{first_chapter}" по "{last_chapter}"'
                        else:
                            chapters = f'Глав {valid_chapters} из {total_chapters}, по "{last_chapter}"'
                    else:
                        chapters = f'Глав {valid_chapters} из {total_chapters}'
                self.temp.chapters = total_chapters

        result = ""
        if book_title and book_url:
            result += f'<a href="{book_url}">{book_title}</a>\n'
        elif book_title:
            result += f'{book_title}\n'
        
        if len(authors) > 0:
            _a: str = ', '.join(authors)
            if len(authors) > 1:
                result += f'Авторы: {_a}\n'
            else:
                result += f'Автор: {_a}\n'
        
        if seria_name and seria_url:
            result += f'Серия: <a href="{seria_url}">{seria_name}</a>\n'
        elif seria_name:
            result += f'Серия: {seria_name}\n'
        
        if chapters:
            result += "\n"
            result += f'{chapters}'

        hashtags = self.__prepare_hashtags(hashtags)
        
        if hashtags:
            result += "\n"
            result += "\n"
            result += ' '.join(hashtags)

        return result

    # external data transfer

    async def __status(self):

        if self.message == self.prev_message:
            return

        status = schemas.DownloadStatus(
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

        self.__set_message(self.message)

    async def __error(self, err: Exception):
        if self.__is_step__(variables.DownloaderStep.CANCELLED):
            return

        self.__set_step(variables.DownloaderStep.ERROR)
        self.temp.text = 'Произошла ошибка'
        proc_err = False
        if getattr(self,'proc'):
            error = await self.proc.stderr.read(-1)
            if error:
                error = error.strip().decode(self.decoder, errors='ignore')
                if error:
                    proc_err = True
                    self.temp.text = self.temp.text + ' <pre>\n'+ self.__escape_err( error ) +'\n</pre>'
        if err and not proc_err:
            self.temp.text = self.temp.text + ' <pre>\n'+ self.__escape_err( str(err) ) +'\n</pre>'

    async def __result(self):

        if self.__is_step__( variables.DownloaderStep.ERROR ) or self.__is_step__( variables.DownloaderStep.CANCELLED ):
            try:
                if self._folder:
                    shutil.rmtree( self._folder )
            except:
                pass
            self.temp.cover = ""
            self.temp.result_files = []
        try:
            if self._folder:
                shutil.rmtree( self._temp )
        except:
            pass

        if self.__is_step__( variables.DownloaderStep.CANCELLED ):
            return
        
        result = schemas.DownloadResult(
            task_id =    self.request.task_id,
            user_id =    self.request.user_id,
            bot_id =     self.request.bot_id,
            web_id =     self.request.web_id,
            chat_id =    self.request.chat_id,
            message_id = self.request.message_id,
            status =     self.step,
            site =       self.request.site,
            text =       self.temp.text,
            cover =      self.temp.cover,
            files =      self.temp.result_files,
            orig_size =  self.temp.orig_size,
            oper_size =  self.temp.oper_size,
            folder =     self._folder
        )

        self.results.put( result.model_dump() )

        sys.exit(0)