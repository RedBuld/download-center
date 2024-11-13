from __future__ import annotations
from typing import List, Dict, Any
from app import variables
from app import models

class QueueWaiting():
    groups: Dict[ str, QueueWaitingGroup ] = {}

    def __init__(
            self,
            groups: Dict[ str, QueueWaitingGroup ] = {},
        ) -> None:
        self.groups = groups

    def __repr__( self ) -> str:
        return '<QueueWaiting>'
    
    #

    async def Export( self ) -> List[Dict]:
        result = []
        for group_name in self.groups.keys():
            result.append({
                "name": group_name,
                "tasks": await self.groups[group_name].GetTasks()
            })
        return result

    async def GetActiveGroups( self ) -> List[str]:
        return list( self.groups.keys() )

    #

    async def GroupInit(
            self,
            group_name: str
        ) -> bool:
        if group_name not in self.groups:
            self.groups[ group_name ] = QueueWaitingGroup()
        return True

    async def GroupDestroy(
            self,
            group_name: str
        ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            del self.groups[ group_name ]
        return True

    async def GroupExists(
            self,
            group_name: str
        ) -> bool:
        ok: bool = group_name in self.groups
        return ok
    
    #
    
    async def GroupGetTasks(
            self,
            group_name: str
        ) -> List[ QueueWaitingTask ] | None:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].GetTasks()
        return None
    
    async def GroupGetTask(
            self,
            group_name: str,
            task_id: int
        ) -> QueueWaitingTask | None:
        ok: bool = group_name in self.groups
        if ok:
            task_ok: bool = task_id in self.groups[ group_name ].tasks
            if task_ok:
                task: QueueWaitingTask = self.groups[ group_name ].tasks[ task_id ]
                return task
        return None

    async def GroupAddTask(
            self,
            group_name: str,
            task: QueueWaitingTask
        ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].AddTask( task )
        return False
    
    async def RemoveTask(
            self,
            task_id: int
        ) -> bool:
        for group_name in self.groups.keys():
            await self.groups[ group_name ].RemoveTask(task_id)
        return True

class QueueWaitingGroup():
    tasks: Dict[ int, QueueWaitingTask ] = {}
    
    def __init__( self ) -> None:
        self.tasks = {}

    def __repr__( self ) -> str:
        return '<QueueWaitingGroup>'
    
    async def GetTasks( self ) -> List[QueueWaitingTask]:
        return [ task for _, task in self.tasks.items() ]

    async def AddTask(
            self,
            task: QueueWaitingTask
        ) -> bool:
        if task.task_id not in self.tasks:
            self.tasks[ task.task_id ] = task
        return True
    
    async def RemoveTask(
            self,
            task_id: int
        ) -> bool:
        if task_id in self.tasks:
            del self.tasks[ task_id ]
        return True

class QueueWaitingTask():
    task_id: int = 0
    site:    str = ""
    url:    str = ""
    request: models.DownloadRequest

    def __init__(
            self,
            task_id: int,
            request: models.DownloadRequest,
        ) -> None:
        self.task_id = task_id
        self.request = request
        self.site = request.site
        self.url = request.url

    def __repr__( self ) -> str:
        return '<QueueWaitingTask '+str( {
            'task_id': self.task_id,
            'request': self.request,
            'site': self.site,
        } )+'>'