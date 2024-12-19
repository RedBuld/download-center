from __future__ import annotations
import os
import asyncio
import traceback
import logging
import shutil
from multiprocessing import Process, Queue
from typing import List, Dict, Any
from app import dto, variables
from app.objects import DB, RD, IC
from app.configs import GC, DC, QC
from app import variables
from app.variables import QueueWaitingTask
from app.classes.downloader import start_downloader

logger = logging.getLogger( __name__ )

class DownloadsQueue():
    # base
    stop_queue:      bool = False
    stopped_results: bool = False
    stopped_tasks:   bool = False
    
    # maps
    sites_active:    List[ str ] = []
    sites_with_auth: List[ str ] = []
    groups:          List[ str ] = []
    site_to_groups:  variables.QueueSitesGroups
    
    # catchers
    statuses:        Queue = None
    results:         Queue = None
    
    stats:           variables.QueueStats
    waiting:         variables.QueueWaiting
    running:         variables.QueueRunning

    def __init__( self, **kwargs ) -> None:
        self.stop_queue      = False
        self.stopped_results = False
        self.stopped_tasks   = False
        self.sites_active    = []
        self.sites_with_auth = []
        self.groups          = []
        self.site_to_groups  = variables.QueueSitesGroups()
        self.statuses        = Queue()
        self.results         = Queue()
        self.stats           = variables.QueueStats()
        self.waiting         = variables.QueueWaiting()
        self.running         = variables.QueueRunning()

    def __repr__( self ) -> str:
        return '<DownloadsQueue>'


    ### PUBLIC METHODS


    async def Start(self) -> None:
        self.stop_queue = False
        self.tasks_pause = False
        try:
            await self.StartResults()

            await self.StartTasks()

            if GC.restore_tasks:
                await self.restoreTasks()

            asyncio.create_task( self.flushRunner() )
            await asyncio.sleep( 0 )

        except KeyboardInterrupt:
            pass
        except:
            traceback.print_exc()


    async def StartTasks(self) -> None:
        self.stopped_tasks = False
        self.stop_queue_tasks = False
        asyncio.create_task( self.tasksRunner() )
        await asyncio.sleep( 0 )


    async def StartResults(self) -> None:
        self.stopped_results = False
        self.stop_queue_results = False
        asyncio.create_task( self.resultsRunner() )
        await asyncio.sleep( 0 )
    #

    async def Stop( self ) -> None:
        self.stop_queue = True
        self.stop_queue_tasks = True
        self.stop_queue_results = True
        while not self.stopped_results and not self.stopped_tasks:
            await asyncio.sleep( 0.1 )
        self.statuses.close()
        self.results.close()


    async def StopTasks( self ) -> None:
        self.stop_queue_tasks = True
        while not self.stopped_tasks:
            await asyncio.sleep( 0.1 )


    async def StopResults( self ) -> None:
        self.stop_queue_results = True
        while not self.stopped_results:
            await asyncio.sleep( 0.1 )

    #


    async def Close( self ) -> None:
        while not self.stopped_results and not self.stopped_tasks:
            await asyncio.sleep( 0.1 )
        self.statuses.close()
        self.results.close()

    async def Save( self ) -> None:
        await self.stats.Save()


    async def UpdateConfig( self ) -> None:
        await self.setupGroups()
        await self.setupSites()


    async def ExportQueue( self ) -> Dict[ str, Any ]:
        result = {
            "stats":   await self.stats.Export(),
            "running": await self.running.Export(),
            "waiting": await self.waiting.Export(),
        }

        return result

    #

    async def CheckSite(
        self,
        site_name: str
    ) -> dto.SiteCheckResponse:
        response = dto.SiteCheckResponse()

        if site_name not in self.sites_active:
            return response

        groups = await self.site_to_groups.GetSiteGroups( site_name )
        if len(groups) == 0:
            return response

        response.allowed = True

        site_config = QC.sites[ site_name ] if site_name in QC.sites else None
        if site_config is None:
            return response

        response.parameters = site_config.parameters

        _formats = site_config.formats
        if not _formats:
            for group_name in groups:
                group_config = None
                if group_name in QC.groups:
                    group_config = QC.groups[ group_name ]
                else:
                    continue
                for format in group_config.formats:
                    if format not in _formats:
                        _formats.append( format )
        
        formats = {}
        for format in _formats:
            if format in QC.formats_params:
                formats[ format ] = QC.formats_params[ format ]

        response.formats = formats

        return response


    async def GetSitesWithAuth( self ) -> dto.SiteListResponse:
        response = dto.SiteListResponse(
            sites = self.sites_with_auth
        )
        return response


    async def GetSitesActive( self ) -> dto.SiteListResponse:
        response = dto.SiteListResponse(
            sites = self.sites_active
        )
        return response
    
    #

    async def AddTask(
        self,
        request: dto.DownloadRequest,
        is_restore: bool = False
    ) -> dto.DownloadResponse:
        logger.info( 'DQ: received request:' + str( request ) )
        response = dto.DownloadResponse()

        site_name = request.site
        
        group_name = await self.site_to_groups.GetSiteGroup( site_name, request.format )
        if not group_name:
            raise Exception( f'Не найдена конфигурация группы для сайта {site_name}' )

        site_config = QC.sites[ site_name ] if site_name in QC.sites else None
        if not site_config:
            raise Exception( f'Не найдена конфигурация для сайта {site_name}' )

        if site_config.force_proxy:
            if not request.proxy and QC.proxies.Has():
                request.proxy = await QC.proxies.GetInstance( site_name, site_config.excluded_proxy )
            if not request.proxy:
                raise Exception( 'Сайт недоступен без прокси' )
        
        can_be_added = await self.stats.GroupCanAdd( group_name )
        if not can_be_added and not is_restore:
            raise variables.QueueCheckException( 'Максимум ожидающих загрузок для группы' )

        can_be_added = await self.stats.SiteCanAdd( site_name )
        if not can_be_added and not is_restore:
            raise variables.QueueCheckException( 'Максимум ожидающих загрузок для сайта' )

        can_be_added = await self.stats.UserCanAdd( request.user_id, site_name, group_name )
        if not can_be_added and not is_restore:
            raise variables.QueueCheckException( 'Максимум ожидающих загрузок для сайта/группы' )
        
        waiting_duplicate = await self.waiting.CheckDuplicate( group_name, request )
        if waiting_duplicate and not is_restore:
            raise variables.QueueCheckException( 'Такая загрузка уже добавлена в очередь' )

        running_duplicate = await self.running.CheckDuplicate( request )
        if running_duplicate and not is_restore:
            raise variables.QueueCheckException( 'Такая загрузка уже загружается' )

        if request.task_id is None: # Maybe restoring task
            try:
                stored_request = await asyncio.wait_for( DB.SaveDownloadRequest( request ), timeout=5.0 )
                request = stored_request.to_dto()
            except:
                raise Exception( "База данных недоступна или перегружена" )

        await self.stats.AddWaiting( request.user_id, site_name, group_name )
        await self.waiting.AddTask( group_name, request )
        
        response.status = True
        response.message = str( request.task_id )

        return response


    async def CancelTask(
        self,
        cancel_request: dto.DownloadCancelRequest
    ) -> dto.DownloadCancelResponse | None:
        logger.info( 'DQ: cancel task:' + str( cancel_request.model_dump() ) )

        try:
            request = await DB.GetDownloadRequest( cancel_request.task_id )

            waiting_task = await self.waiting.RemoveTask( cancel_request.task_id )
            if waiting_task != None:
                await self.stats.RemoveWaiting( waiting_task.user_id, waiting_task.site, waiting_task.group )

            running_task = await self.running.RemoveTask( cancel_request.task_id )
            if running_task != None:
                await self.stats.RemoveRun( running_task.user_id, running_task.site, running_task.group, running_task.request.proxy )

            await DB.DeleteDownloadRequest( cancel_request.task_id )

            if waiting_task != None:
                return dto.DownloadCancelResponse.model_validate( waiting_task.request, from_attributes=True )
            if running_task != None:
                return dto.DownloadCancelResponse.model_validate( running_task.request, from_attributes=True )
            if request != None:
                return dto.DownloadCancelResponse.model_validate( request.to_dto(), from_attributes=True )
            return None
        except:
            traceback.print_exc()
            return None


    async def ClearFolder(
        self,
        clear_request: dto.DownloadClearRequest
    ) -> None:
        if clear_request.task_id:
            try:
                result_dir = os.path.join( DC.save_folder, str( clear_request.task_id ) )
                if os.path.isdir( result_dir ):
                    shutil.rmtree( result_dir )
            except:
                pass
            try:
                archive_dir = os.path.join( DC.arch_folder, str( clear_request.task_id ) )
                if os.path.isdir( archive_dir ):
                    shutil.rmtree( archive_dir )
            except:
                pass


    ### PRIVATE METHODS
    
    async def restoreTasks( self ) -> None:
        logger.info( 'DQ: restoreTasks started' )

        results = await DB.GetAllDownloadResults()
        for result in results:
            logger.info( 'DQ: restoreTasks result: ' + str( result ) )
            asyncio.create_task( self.sendFiles( result.to_dto() ) )
            await asyncio.sleep( 0.1 )

        requests = await DB.GetAllDownloadRequests()
        for request in requests:
            logger.info( 'DQ: restoreTasks request: ' + str( request ) )
            asyncio.create_task( self.AddTask( request.to_dto(), True ) )
            await asyncio.sleep( 0.1 )

        logger.info( 'DQ: restoreTasks done' )
    
    #

    async def flushRunner( self ) -> None:
        logger.info( 'DQ: flushRunner started' )
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
        logger.info( 'DQ: flushRunner started' )


    async def resultsRunner( self ) -> None:
        logger.info( 'DQ: resultsRunner started' )
        while True:
            await asyncio.sleep(1)
            try:
                while not self.results.empty():
                    json_result = self.results.get()

                    await self.taskDone( dto.DownloadResult( **json_result ) )

                    if self.stop_queue_results:
                        break

                while not self.statuses.empty():
                    json_status = self.statuses.get()

                    await self.taskStatus( dto.DownloadStatus( **json_status ) )

                    if self.stop_queue_results:
                        break

            except:
                traceback.print_exc()
            if self.stop_queue_results:
                break
        self.stopped_results = True
        logger.info('DQ: resultsRunner stopped')


    async def tasksRunner( self ) -> None:
        logger.info('DQ: tasksRunner started')
        while True:
            await asyncio.sleep(1)
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
                                # logger.info( f'DQ: group {group_name} can\'t run' )
                                continue

                            # go over waiting tasks
                            for task in tasks:

                                if not await self.stats.GroupCanStart( group_name, task.request.proxy ):
                                    continue

                                # check site
                                site_name = task.request.site
                                if not await self.stats.SiteCanStart( site_name, task.request.proxy ):
                                    # logger.info( f'DQ: site {site_name} can\'t run')
                                    continue

                                # check user
                                user_id = task.request.user_id
                                if not await self.stats.UserCanStart( user_id, site_name, group_name, task.request.proxy ):
                                    # logger.info( f'DQ: user {user_id} can\'t run' )
                                    continue

                                task_id = task.task_id
                                if await self.taskRun( task ):
                                    await self.waiting.RemoveTask( task_id )
                    except:
                        traceback.print_exc()
            except:
                traceback.print_exc()

            if self.stop_queue_tasks:
                break

        self.stopped_tasks = True
        logger.info('DQ: tasksRunner stopped')

    ###

    async def taskRun(
        self,
        waiting_task: QueueWaitingTask
    ) -> bool:
        logger.info('DQ: taskRun')

        try:
            task_id = waiting_task.task_id
            user_id = waiting_task.request.user_id
            site_name = waiting_task.request.site
            format = waiting_task.request.format
            group_name = await self.site_to_groups.GetSiteGroup( site_name, format )

            if group_name:
                running_task = await self.running.AddTask( group_name, waiting_task.request )
                if running_task:

                    downloader   = DC.downloaders[ QC.sites[ site_name ].downloader or QC.groups[ group_name ].downloader ]
                    pattern      = waiting_task.request.filename or QC.sites[ site_name ].pattern or QC.groups[ group_name ].pattern or '{Book.Title}'
                    page_delay   = QC.sites[ site_name ].page_delay or QC.groups[ group_name ].page_delay or 0
                    flaresolverr = ''
                    if QC.sites[ site_name ].use_flare:
                        if waiting_task.request.proxy and QC.flaresolverrs.Has():
                            flaresolverr = await QC.flaresolverrs.GetInstance( waiting_task.request.proxy )
                        else:
                            flaresolverr = GC.flaresolverr

                    context = variables.DownloaderContext(
                        save_folder  = DC.save_folder,
                        exec_folder  = DC.exec_folder,
                        temp_folder  = DC.temp_folder,
                        arch_folder  = DC.arch_folder,
                        compression  = DC.compression,
                        file_limit   = DC.file_limit,
                        downloader   = downloader,
                        page_delay   = page_delay,
                        pattern      = pattern,
                        flaresolverr = flaresolverr
                    )

                    running_task.proc = Process(
                        target = start_downloader,
                        name   = f"Downloader #{waiting_task.task_id} [{waiting_task.request.url}]",
                        kwargs = {
                            'request':  waiting_task.request,
                            'context':  context,
                            'statuses': self.statuses,
                            'results':  self.results,
                        },
                        daemon = True
                    )
                    running_task.proc.start()

                    await self.stats.AddRun( user_id, site_name, group_name, waiting_task.request.proxy )
                    await self.stats.RemoveWaiting( user_id, site_name, group_name )

                    logger.info( f'DQ: started task {task_id}: ' + str(running_task.proc) )

                    return True
        except:
            traceback.print_exc()
            return False
    
    #

    async def taskStatus(
        self,
        status: dto.DownloadStatus
    ) -> None:
        if not await self.running.Exists( status.task_id ):
            return
        
        await self.running.UpdateStatus( status.task_id, status.text )

        await IC.Send(status)

    #

    async def taskDone(
        self,
        result: dto.DownloadResult
    ) -> None:
        logger.info('DQ: taskDone')

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

        await DB.SaveDownloadResult( result )
        await DB.DeleteDownloadRequest( task_id )
        await DB.AddDownloadHistory( result )

        asyncio.create_task( self.sendFiles( result ) )
        await asyncio.sleep( 0 )


    async def sendFiles(self, result: dto.DownloadResult) -> None:

        if result.text == '':
            result.text = 'нет описания'

        sended = await IC.Send(result)

        if sended:
            await DB.DeleteDownloadResult( result.task_id )
            logger.info( 'deleted result, task #' + str( result.task_id ) )

        try:
            await DB.UpdateSiteStat( result )
        except:
            traceback.print_exc()

    #

    async def setupGroups( self ) -> None:
        groups = QC.groups

        active_groups: List[ str ] = []
        waiting_active_groups = await self.waiting.GetActiveGroups()
        stats_active_groups = await self.stats.GetActiveGroups()

        for group_name in groups:            
            await self.stats.GroupInit( group_name )
            await self.waiting.GroupInit( group_name )

            if group_name not in active_groups:
                active_groups.append( group_name )

        # clean abandoned stats groups
        for group_name in stats_active_groups:
            if group_name not in active_groups:
                if await self.stats.GroupNotBusy( group_name ):
                    await self.stats.GroupDestroy( group_name )

        # clean abandoned waiting queue groups
        for group_name in waiting_active_groups:
            if group_name not in active_groups:
                if await self.stats.GroupNotBusy( group_name ):
                    await self.waiting.GroupDestroy( group_name )

        self.groups = active_groups

    #

    async def setupSites( self ) -> None:
        sites = QC.sites

        sites_with_auth: List[ str ] = []
        sites_active: List[ str ] = []

        stg_active_sites = await self.site_to_groups.GetActiveSites()
        stats_active_sites = await self.stats.GetActiveSites()

        for site_name in sites:
            site_config = sites[ site_name ]

            await self.stats.SiteInit( site_name )
            await self.site_to_groups.SiteInit( site_name, site_config.allowed_groups )

            if 'auth' in site_config.parameters:
                sites_with_auth.append( site_name )

            if site_config.active:
                if site_name not in sites_active:
                    sites_active.append( site_name )

        self.sites_with_auth = sites_with_auth
        self.sites_active = sites_active

        # clean abandoned stats groups
        for site_name in stats_active_sites:
            if site_name not in sites_active:
                if await self.stats.SiteNotBusy( site_name ):
                    await self.stats.SiteDestroy( site_name )

        # clean abandoned stats groups
        for site_name in stg_active_sites:
            if site_name not in sites_active:
                if await self.stats.SiteNotBusy( site_name ):
                    await self.site_to_groups.SiteDestroy( site_name )