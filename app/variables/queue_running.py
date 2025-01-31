from __future__ import annotations
import asyncio
from typing import List, Dict
from multiprocessing import Process
from app import dto

class QueueRunning():
    tasks: Dict[ int, QueueRunningTask ] = {}
    
    def __init__(
        self,
        tasks: Dict[ int, QueueRunningTask ] = {}
    ) -> None:
        self.tasks = tasks

    def __repr__( self ) -> str:
        return '<QueueRunning>'
    
    #

    async def Export( self ) -> List[ Dict ]:
        _temp = {}

        for _, task in self.tasks.items():
            if task.group not in _temp:
                _temp[ task.group ] = {
                    "name": task.group,
                    "tasks": []
                }
            _temp[ task.group ][ 'tasks' ].append( task )

        result = [ _g for _, _g in _temp.items() ]
        return result
    
    #

    # Check that download with same config does not exists
    async def CheckDuplicate(
        self,
        request: dto.DownloadRequest
    ) -> bool:
        for _, task in self.tasks.items():
            if task.request.user_id == request.user_id and task.request.url == request.url \
                and \
               task.request.start == request.start and task.request.end == request.end \
                and \
               task.request.images == request.images:
                return True
        return False
    
    #
    
    # Check that tasks exists in queue
    async def Exists(
        self,
        task_id: int
    ) -> bool:
        ok: bool = task_id in self.tasks
        return ok

    # Get task from queue
    async def GetTask(
        self,
        task_id: int
    ) -> QueueRunningTask | None:
        ok: bool = task_id in self.tasks
        if ok:
            task: QueueRunningTask = self.tasks[ task_id ]
            return task
        return None

    # Add task to queue
    async def AddTask(
        self,
        group_name: str,
        proxy:      str,
        request:    dto.DownloadRequest
    ) -> QueueRunningTask | None:
        if request.task_id not in self.tasks:
            task = QueueRunningTask(
                group   = group_name,
                proxy   = proxy,
                request = request
            )
            self.tasks[ task.task_id ] = task

        ok: bool = request.task_id in self.tasks
        if ok:
            task: QueueRunningTask = self.tasks[ request.task_id ]
            return task
        return None

    # Remove task from queue
    async def RemoveTask(
        self,
        task_id: int
    ) -> QueueRunningTask | None:
        task: QueueRunningTask = await self.GetTask( task_id )
        if task:
            if task.proc:
                task.proc.terminate()
                while task.proc.is_alive():
                    await asyncio.sleep( 0.1 )
                task.proc.close()
            del self.tasks[ task_id ]
            return task
        return None

    # Update running task last status for queue monitoring
    async def UpdateStatus(
        self,
        task_id: int,
        status:  str
    ) -> bool:
        ok: bool = task_id in self.tasks
        if ok:
            self.tasks[ task_id ].status = status
            return True
        return False

class QueueRunningTask():
    task_id: int = 0
    user_id: int = 0
    site:    str = ""
    group:   str = ""
    url:     str = ""
    proxy:   str = ""
    request: dto.DownloadRequest
    status:  str = ""
    proc:    Process

    def __init__(
        self,
        group:   str,
        proxy:   str,
        request: dto.DownloadRequest
    ) -> None:
        self.task_id = request.task_id
        self.user_id = request.user_id
        self.site    = request.site
        self.group   = group
        self.url     = request.url
        self.proxy   = proxy
        self.request = request
        self.status  = "Ожидает запуска"

    def __repr__( self ) -> str:
        return '<QueueRunningTask '+str( {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'site':    self.site,
            'url':     self.url,
            'proxy':   self.proxy,
            'group':   self.group,
            'status':  self.status,
        } )+'>'
    

    
