from __future__ import annotations
import os
import asyncio
import traceback
import logging
import shutil
from datetime import datetime, timedelta
from ctypes import c_bool
from multiprocessing import Process, Queue
from typing import List, Dict, Any
from app import variables, schemas
from app.objects import DB, RD, IC
from app.configs import GC, DC, QC
from app import variables
from app import models
from app.variables import QueueStats, QueueWaiting, QueueWaitingTask, QueueRunning, QueueSitesGroups
from app.classes.downloader import start_downloader

logger = logging.getLogger(__name__)

class DownloadsQueue():
    # base
    checkInterval:   float = 1.0
    stop_queue:      bool = False
    stopped_results: bool = False
    stopped_tasks:   bool = False
    
    # maps
    active:          List[ str ] = []
    auths:           List[ str ] = []
    groups:          List[ str ] = []
    site_to_groups:  QueueSitesGroups
    
    # catchers
    statuses:        Queue = None
    results:         Queue = None
    
    # realtime stats
    stats:           QueueStats
    # tasks
    waiting:         QueueWaiting
    running:         QueueRunning

    def __init__( self, **kwargs ) -> None:
        self.groups =          []
        self.auths =           []
        self.stats =           QueueStats()
        self.waiting =         QueueWaiting()
        self.running =         QueueRunning()
        self.site_to_groups =  QueueSitesGroups()
        self.stop_queue =      False
        self.stopped_results = False
        self.stopped_tasks =   False
        self.statuses =        Queue()
        self.results =         Queue()

    def __repr__( self ) -> str:
        return '<DownloadsQueue>'
    
    ### PUBLIC METHODS
    
    async def Start(self) -> None:
        self.stop_queue = False
        self.stopped_results = False
        self.stopped_tasks = False
        self.tasks_pause = False
        try:
            asyncio.create_task( self.__results_runner() )
            await asyncio.sleep( 0 )

            asyncio.create_task( self.__tasks_runner() )
            await asyncio.sleep( 0 )

            if GC.restore_tasks:
                await self.__restore_tasks()

            asyncio.create_task( self.__stats_flush_runner() )
            await asyncio.sleep( 0 )

        except KeyboardInterrupt:
            pass
        except:
            traceback.print_exc()

    async def Stop(self) -> None:
        self.stop_queue = True
        while not self.stopped_results and not self.stopped_tasks:
            await asyncio.sleep(0.1)
        self.statuses.close()
        self.results.close()
    
    async def Save(self) -> None:
        await self.stats.Save()

    async def UpdateConfig(self) -> None:

        await self.__setup_groups(QC.groups)
        await self.__setup_sites(QC.sites)
    
    async def ExportQueue(self) -> Dict[str,Any]:
        result = {
            "stats": await self.stats.Export(),
            "running": await self.running.Export(),
            "waiting": await self.waiting.Export(),
        }

        return result

    #

    async def CheckSite(self, site_name: str) -> tuple[bool, list[str], Dict[str,list[str]]]:
        if site_name not in self.active:
            return False, [], {}

        groups = await self.site_to_groups.GetSiteGroups( site_name )
        if len(groups) == 0:
            return False, [], {}

        site_config = QC.sites[ site_name ] if site_name in QC.sites else None
        if site_config is None:
            return True, [], {}

        _formats = site_config.formats
        if not _formats:
            _formats = []
            for group_name in groups:
                group_config = QC.groups[ group_name ] if group_name in QC.groups else None
                if not group_config:
                    return True, [], {}
                for format in group_config.formats:
                    if format not in _formats:
                        _formats.append(format)
        
        formats = {}
        for format in _formats:
            if format in QC.formats_params:
                formats[ format ] = QC.formats_params[ format ]

        return True, site_config.parameters, formats

    async def GetSitesWithAuth(self) -> List[str]:
        return self.auths

    async def GetSitesActive(self) -> List[str]:
        return [x for x in self.active if x != 'audiolitres.ru']
    
    #

    async def AddTask(self, request: schemas.DownloadRequest, raise_on_limit: bool = True) -> schemas.DownloadResponse:
        logger.info( 'DQ: received request:' + str( request ) )

        site_name = request.site
        
        group_name = await self.site_to_groups.GetSiteGroup( site_name, request.format )
        if group_name:

            site_config = QC.sites[ site_name ] if site_name in QC.sites else None

            if site_config.force_proxy:
                if not request.proxy:
                    if request.task_id is None and QC.proxies.has():
                        request.proxy = await QC.proxies.getProxy( site_name )
                    else:
                        raise Exception("Сайт недоступен без прокси")
            
            can_be_added = await self.stats.GroupCanAdd( group_name )
            if not can_be_added and raise_on_limit:
                raise variables.QueueCheckException('Максимум ожидающих загрузок для группы')

            can_be_added = await self.stats.SiteCanAdd( site_name )
            if not can_be_added and raise_on_limit:
                raise variables.QueueCheckException('Максимум ожидающих загрузок для сайта')

            can_be_added = await self.stats.UserCanAdd( request.user_id, site_name, group_name )
            if not can_be_added and raise_on_limit:
                raise variables.QueueCheckException('Максимум ожидающих загрузок для сайта/группы')
            
            waiting_duplicate = await self.waiting.CheckDuplicate( group_name, request )
            running_duplicate = await self.running.CheckDuplicate( request )

            if waiting_duplicate:
                raise variables.QueueCheckException('Такая загрузка уже добавлена в очередь')

            if running_duplicate:
                raise variables.QueueCheckException('Такая загрузка уже загружается')

            if request.task_id is None: # Maybe restoring task
                try:
                    request = await asyncio.wait_for( DB.SaveRequest( request.model_dump() ), timeout=5.0 )
                except ( asyncio.TimeoutError, asyncio.CancelledError ):
                    return schemas.DownloadResponse(
                        status =  False,
                        message = "База данных недоступна или перегружена"
                    )

            waiting_task = QueueWaitingTask(
                task_id = request.task_id,
                group =   group_name,
                request = request
            )

            await self.stats.AddWaiting( request.user_id, site_name, group_name )
            await self.waiting.GroupAddTask( group_name, waiting_task )
        
        return schemas.DownloadResponse(
            status =  True,
            message = str(request.task_id)
        )

    async def CancelTask(self, cancel_request: schemas.DownloadCancelRequest) -> bool | schemas.SiteListResponse:
        logger.info( 'DQ: cancel task:' + str( cancel_request.model_dump() ) )

        try:
            waiting_task = await self.waiting.RemoveTask( cancel_request.task_id )
            if waiting_task != False:
                await self.stats.RemoveWaiting( waiting_task.user_id, waiting_task.site, waiting_task.group )

            running_task = await self.running.RemoveTask( cancel_request.task_id )
            if running_task != False:
                await self.stats.RemoveRun( running_task.user_id, running_task.site, running_task.group, running_task.request.proxy )

            await DB.DeleteRequest( cancel_request.task_id )

            if waiting_task != False:
                return schemas.DownloadCancelResponse.model_validate(waiting_task.request, from_attributes=True)
            if running_task != False:
                return schemas.DownloadCancelResponse.model_validate(running_task.request, from_attributes=True)
            return False
        except:
            traceback.print_exc()
            return False
    
    async def ClearFolder(self, clear_request: schemas.DownloadClearRequest) -> None:
        if clear_request.folder:
            if os.path.isdir(clear_request.folder):
                shutil.rmtree( clear_request.folder )


    ### PRIVATE METHODS
    
    async def __restore_tasks(self) -> None:
        logger.info( 'DQ: __restore_tasks started' )

        requests = await DB.GetAllRequests()
        for request in requests:
            logger.info( 'DQ: __restore_tasks request: ' + str( request ) )
            asyncio.create_task( self.AddTask( schemas.DownloadRequest.model_validate(request), False ) )
            await asyncio.sleep( 0 )

        results = await DB.GetAllResults()
        for result in results:
            logger.info( 'DQ: __restore_tasks result: ' + str( result ) )
            asyncio.create_task( self.__send_files( schemas.DownloadResult.model_validate(result) ) )
            await asyncio.sleep( 0 )

        logger.info( 'DQ: __restore_tasks done' )
    
    #

    async def __stats_flush_runner(self) -> None:
        while True:
            await asyncio.sleep(300)
            try:
                self.tasks_pause = True
                await self.stats.Flush()
                self.tasks_pause = False
            except:
                traceback.print_exc()
            if self.stop_queue:
                break

    async def __results_runner(self) -> None:
        logger.info( 'DQ: __results_runner started' )
        while True:
            # logger.info('__results_runner tick')
            try:
                while not self.results.empty():
                    json_result = self.results.get()

                    await self.__task_done( schemas.DownloadResult( **json_result ) )

                    if self.stop_queue:
                        break

                while not self.statuses.empty():
                    json_status = self.statuses.get()

                    await self.__task_status( schemas.DownloadStatus( **json_status ) )

                    if self.stop_queue:
                        break

            except:
                traceback.print_exc()
            if self.stop_queue:
                break
            await asyncio.sleep(1)
        self.stopped_results = True

        logger.info('DQ: __results_runner stopped')
        
    async def __tasks_runner(self) -> None:
        logger.info('DQ: __tasks_runner started')
        i = 0
        while True:
            # logger.info('__tasks_runner tick')
            try:
                if self.tasks_pause:
                    await asyncio.sleep(1)
                    continue
                for group_name in self.groups:
                    try:
                        wg_exists = await self.waiting.GroupExists( group_name )
                        if wg_exists:

                            # preventive skip empty group
                            tasks = await self.waiting.GroupGetTasks( group_name )
                            if len(tasks) == 0:
                                continue

                            # preventive skip group
                            if not await self.stats.GroupCanStart( group_name ):
                                continue
                                # logger.info('DQ: group tasks: '+str(tasks))
                            # if i == 0:
                            #     logger.info(f'DQ: group {group_name} can run')

                            # go over waiting tasks
                            for task in tasks:

                                if not await self.stats.GroupCanStart( group_name, task.request.proxy ):
                                    # logger.info('DQ: group can\'t run')
                                    continue

                                # check site
                                site_name = task.request.site
                                if not await self.stats.SiteCanStart( site_name, task.request.proxy ):
                                    # logger.info('DQ: site can\'t run')
                                    continue
                                # if i == 0:
                                #     logger.info(f'DQ: site {site_name} can run')

                                # check user
                                user_id = task.request.user_id
                                if not await self.stats.UserCanStart( user_id, site_name, group_name, task.request.proxy ):
                                    # if i == 0:
                                    #     logger.info(f'DQ: user {user_id} can\'t run')
                                    continue
                                # if i == 0:
                                #     logger.info(f'DQ: user {user_id} can run')

                                task_id = task.task_id
                                await self.waiting.RemoveTask( task_id )

                                await self.__task_start( task )
                    except:
                        traceback.print_exc()
            except:
                traceback.print_exc()
            finally:
                if i == 0:
                    i = 1
                else:
                    i = 0

            if self.stop_queue:
                break
            await asyncio.sleep(1)
        self.stopped_tasks = True
        logger.info('DQ: __tasks_runner stopped')

    ###

    async def __task_start(self, waiting_task: QueueWaitingTask) -> None:
        logger.info('DQ: __task_start')

        try:
            task_id = waiting_task.task_id
            user_id = waiting_task.request.user_id
            site_name = waiting_task.request.site
            format = waiting_task.request.format
            group_name = await self.site_to_groups.GetSiteGroup( site_name, format )

            if group_name:
                
                running_task = await self.running.AddTask( task_id, group_name, waiting_task.request )

                if running_task:

                    pattern = waiting_task.request.filename or QC.sites[ site_name ].pattern or QC.groups[ group_name ].pattern or '{Book.Title}'
                    # pattern = pattern.translate(
                    #     str.maketrans({
                    #         '[': '\\[',
                    #         ']': '\\]',
                    #     })
                    # )

                    context = variables.DownloaderContext(
                        save_folder =  DC.save_folder,
                        exec_folder =  DC.exec_folder,
                        temp_folder =  DC.temp_folder,
                        arch_folder =  DC.arch_folder,
                        compression =  DC.compression,
                        downloader =   DC.downloaders[ QC.sites[ site_name ].downloader ],
                        page_delay =   QC.sites[ site_name ].page_delay,
                        pattern =      pattern,
                        flaresolverr = GC.flaresolverr if QC.sites[ site_name ].use_flare else ''
                    )

                    running_task.proc = Process(
                        target=start_downloader,
                        name="Downloader #"+str(waiting_task.task_id),
                        kwargs={
                            'request':     waiting_task.request,
                            'context':     context,
                            'statuses':    self.statuses,
                            'results':     self.results,
                        },
                        daemon=True
                    )
                    running_task.proc.start()

                    await self.stats.AddRun( user_id, site_name, group_name, waiting_task.request.proxy )
                    await self.stats.RemoveWaiting( user_id, site_name, group_name )

                    logger.info(f'DQ: started task {task_id}:' + str(running_task.proc) )
        except:
            traceback.print_exc()
    
    #

    async def __task_status(self, status: schemas.DownloadStatus) -> None:
        # logger.info('DQ: __task_status')

        if not await self.running.Exists( status.task_id ):
            return
        
        await self.running.UpdateStatus( status.task_id, status.text )

        await IC.Send(status)

    #

    async def __task_done(self, result: schemas.DownloadResult) -> None:
        logger.info('DQ: __task_done')

        task_id = result.task_id

        try:
            task = await self.running.GetTask( task_id )
            
            if task:
                user_id = task.user_id
                site_name = task.site
                group_name = task.group

                if await self.running.Exists( task_id ):
                    await self.running.RemoveTask( task_id )

                await self.stats.RemoveRun( user_id, site_name, group_name, result.proxy )
            else:
                raise Exception("Task not found")

        except:
            traceback.print_exc()

        await DB.SaveResult( result.model_dump(exclude=['dbg_log','dbg_config']) )
        await DB.DeleteRequest( task_id )
        await DB.AddHistory( result.model_dump() )

        await self.__send_files( result )

    async def __send_files(self, result: schemas.DownloadResult) -> None:

        if result.text == '':
            result.text = 'нет описания'

        sended = await IC.Send(result)

        if sended:
            await DB.DeleteResult( result.task_id )
            logger.info( 'deleted result, task #' + str( result.task_id ) )

        try:
            await DB.UpdateSiteStat( result.model_dump() )
        except:
            traceback.print_exc()

    #

    async def __setup_groups(self, groups: Dict[str, variables.QueueConfigGroup]) -> None:
        active_groups: List[str] = []
        waiting_active_groups = await self.waiting.GetActiveGroups()
        stats_active_groups = await self.stats.GetActiveGroups()

        for group_name in groups:            
            await self.stats.GroupInit(group_name)

            await self.waiting.GroupInit(group_name)

            if group_name not in active_groups:
                active_groups.append(group_name)

        # clean abandoned stats groups
        for group_name in stats_active_groups:
            if group_name not in active_groups:
                await self.stats.GroupDestroy(group_name)

        # clean abandoned waiting queue groups
        for group_name in waiting_active_groups:
            if group_name not in active_groups:
                await self.waiting.GroupDestroy(group_name)

        self.groups = active_groups
        pass

    #

    async def __setup_sites(self, sites: Dict[str, variables.QueueConfigSite]) -> None:
        sites_with_auth: List[str] = []
        active_sites: List[str] = []

        stg_active_sites = await self.site_to_groups.GetActiveSites()
        stats_active_sites = await self.stats.GetActiveSites()

        for site_name in sites:

            site_config = sites[site_name]

            if 'auth' in site_config.parameters:
                sites_with_auth.append( site_name )

            await self.stats.SiteInit( site_name )

            if site_config.active:
                await self.site_to_groups.SiteInit( site_name, site_config.allowed_groups )
                if site_name not in active_sites:
                    active_sites.append( site_name )

        self.auths = sites_with_auth
        self.active = active_sites

        # clean abandoned stats groups
        for site_name in stats_active_sites:
            if site_name not in active_sites:
                await self.stats.SiteDestroy( site_name )

        # clean abandoned stats groups
        for site_name in stg_active_sites:
            if site_name not in active_sites:
                await self.site_to_groups.SiteDestroy( site_name )