from __future__ import annotations
import asyncio
from typing import List, Dict, Any
from multiprocessing import Process
from app import models
from app import schemas

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
                _temp[task.group] = {
                    "name": task.group,
                    "tasks": []
                }
            _temp[task.group]['tasks'].append(task)
        result = [ _g for _, _g in _temp.items() ]
        return result
    
    #

    async def CheckDuplicate( self, request: schemas.DownloadRequest ) -> bool:
        for _, task in self.tasks.items():
            if task.request.user_id == request.user_id and task.request.url == request.url \
                and \
               task.request.start == request.start and task.request.end == request.end \
                and \
               task.request.images == request.images:
                return True
        return False
    
    #
    
    async def Exists( self, task_id: int ) -> bool:
        ok: bool = task_id in self.tasks
        return ok

    async def GetTask( self, task_id: int ) -> QueueRunningTask | None:
        ok: bool = task_id in self.tasks
        if ok:
            task: QueueRunningTask = self.tasks[ task_id ]
            return task
        return None

    async def AddTask( self, task_id: int, group_name: str, request: models.DownloadRequest ) -> QueueRunningTask | None:
        if task_id not in self.tasks:
            task = QueueRunningTask(
                task_id =    task_id,
                group =      group_name,
                request =    request
            )
            self.tasks[ task_id ] = task
        return self.tasks[ task_id ] if task_id in self.tasks else None

    async def RemoveTask( self, task_id: int ) -> QueueRunningTask | bool:
        ok: bool = task_id in self.tasks
        if ok:
            task: QueueRunningTask = self.tasks[ task_id ]
            if task:
                if task.proc:
                    task.proc.terminate()
                    while task.proc.is_alive():
                        await asyncio.sleep(0.1)
                    task.proc.close()
                del self.tasks[ task_id ]
                return task
        return False

    async def UpdateStatus( self, task_id: int, status: str ) -> bool:
        ok: bool = task_id in self.tasks
        if ok:
            self.tasks[ task_id ].last_status = status
            return True
        return False

class QueueRunningTask():
    task_id:     int = 0
    user_id:     int = 0
    site:        str = ""
    group:       str = ""
    url:         str = ""
    last_status: str = ""
    request:     models.DownloadRequest
    proc:        Process

    def __init__(
            self,
            task_id: int,
            group:   str,
            request: models.DownloadRequest
        ) -> None:
        self.task_id = task_id
        self.group = group
        self.user_id = request.user_id
        self.site = request.site
        self.url = request.url
        self.last_status = ""
        self.request = request

    def __repr__( self ) -> str:
        return '<QueueRunningTask '+str( {
            'task_id':     self.task_id,
            'user_id':     self.user_id,
            'site':        self.site,
            'url':         self.url,
            'group':       self.group,
            'last_status': self.last_status,
        } )+'>'
    

    
