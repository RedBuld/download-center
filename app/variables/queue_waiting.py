from __future__ import annotations
from typing import List, Dict
from app import dto

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

    async def Export( self ) -> List[ Dict ]:
        result = []
        for group_name in self.groups.keys():
            result.append({
                "name": group_name,
                "tasks": await self.groups[ group_name ].GetTasks()
            })
        return result

    async def GetActiveGroups( self ) -> List[ str ]:
        return list( self.groups.keys() )
    
    #

    # Check that download with same config does not exists
    async def CheckDuplicate(
        self,
        group_name: str,
        request:    dto.DownloadRequest
    ) -> bool:
        for _, task in self.groups[ group_name ].tasks.items():
            if task.request.user_id == request.user_id and task.request.url == request.url \
                and \
               task.request.start == request.start and task.request.end == request.end \
                and \
               task.request.images == request.images:
                return True
        return False

    #

    # Add group to queue
    async def GroupInit(
        self,
        group_name: str
    ) -> bool:
        if group_name not in self.groups:
            self.groups[ group_name ] = QueueWaitingGroup()
        return True

    # Remove group from queue
    async def GroupDestroy(
        self,
        group_name: str
    ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            del self.groups[ group_name ]
        return True

    # Check group exists in queue
    async def GroupExists(
        self,
        group_name: str
    ) -> bool:
        ok: bool = group_name in self.groups
        return ok
    
    #
    
    # Get waiting tasks from group
    async def GroupGetTasks(
        self,
        group_name: str
    ) -> List[ QueueWaitingTask ] | None:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].GetTasks()
        return None
    
    # Get waiting task from group
    async def GroupGetTask(
        self,
        group_name: str,
        task_id:    int
    ) -> QueueWaitingTask | None:
        ok: bool = group_name in self.groups
        if ok:
            task_ok: bool = task_id in self.groups[ group_name ].tasks
            if task_ok:
                task: QueueWaitingTask = self.groups[ group_name ].tasks[ task_id ]
                return task
        return None
    
    #

    # Add task to queue
    async def AddTask(
        self,
        group_name: str,
        request:    dto.DownloadRequest
    ) -> QueueWaitingTask | None:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].AddTask( group_name, request )
        return None

    # Get waiting task from group
    async def RemoveTask(
        self,
        task_id: int
    ) -> QueueWaitingTask | None:
        for group_name in self.groups.keys():
            task = await self.groups[ group_name ].GetTask( task_id )
            if task is not None:
                await self.groups[ group_name ].RemoveTask( task_id )
                return task
        return None

class QueueWaitingGroup():
    tasks: Dict[ int, QueueWaitingTask ] = {}
    
    def __init__( self ) -> None:
        self.tasks = {}

    def __repr__( self ) -> str:
        return '<QueueWaitingGroup>'
    
    # Return list of tasks
    async def GetTasks( self ) -> List[ QueueWaitingTask ]:
        return [ task for _, task in self.tasks.items() ]
    
    # Get task from group
    async def GetTask(
        self,
        task_id: int
    ) -> QueueWaitingTask | None:
        ok: bool = task_id in self.tasks
        if ok:
            task: QueueWaitingTask = self.tasks[ task_id ]
            return task
        return None

    # Add task to group
    async def AddTask(
        self,
        group:   str,
        request: dto.DownloadRequest
    ) -> bool:
        if request.task_id not in self.tasks:
            task = QueueWaitingTask(
                group   = group,
                request = request
            )
            self.tasks[ task.task_id ] = task
        
        ok: bool = request.task_id in self.tasks
        if ok:
            task: QueueWaitingTask = self.tasks[ request.task_id ]
            return task
        return None
    
    # Remove task from group
    async def RemoveTask(
        self,
        task_id: int
    ) -> bool:
        ok: bool = task_id in self.tasks
        if ok:
            del self.tasks[ task_id ]
        return True

class QueueWaitingTask():
    task_id: int = 0
    user_id: int = 0
    site:    str = ""
    group:   str = ""
    url:     str = ""
    request: dto.DownloadRequest

    def __init__(
        self,
        group:   str,
        request: dto.DownloadRequest,
    ) -> None:
        self.task_id = request.task_id
        self.user_id = request.user_id
        self.site    = request.site
        self.group   = group
        self.url     = request.url
        self.request = request

    def __repr__( self ) -> str:
        return '<QueueWaitingTask '+str( {
            'task_id': self.task_id,
            'request': self.request,
            'site':    self.site,
            'url':     self.url,
            'group':   self.group,
        } )+'>'