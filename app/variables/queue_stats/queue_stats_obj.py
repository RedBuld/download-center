from __future__ import annotations

import ujson
from enum import Enum
from typing import List, Dict, Any
from datetime import datetime

from app.objects import RD
from app.configs import QC
from app.variables.queue_config import NONE_USER, MAX_WAIT, MAX_ONETIME, DELAY, WAIT, ONETIME

class QueueStatsObj():
    __type__:  str
    __name__:  str
    __user__:  str = NONE_USER
    waiting:   int = 0 # waiting total
    running:   int = 0 # running total
    running_r: Dict[ str, int ] = {} # running per proxy/raw
    last_run:  Dict[ str, float ] = {} # last run per proxy/raw

    def __init__(
            self,
            __type__: str,
            __name__: str,
            __user__: str = NONE_USER
        ):
        self.__type__  = __type__
        self.__name__  = __name__
        self.__user__  = __user__
        self.waiting   = 0
        self.running   = 0
        self.running_r = {}
        self.last_run  = {}

    @property
    def __json__( self ) -> str:
        return {
            '__type__':  self.__type__,
            '__name__':  self.__name__,
            '__user__':  self.__user__,
            'waiting':   self.waiting,
            'running':   self.running,
            'running_r': self.running_r,
            'last_run':  self.last_run,
        }

    def __repr__( self ) -> str:
        return '<QueueStatsObj '+str( self.__json__ )+'>'

    # Save last_run states
    async def Save( self ) -> None:
        await RD.setex( f"{self.__type__}_{self.__name__}_{self.__user__}", 3600, ujson.dumps(self.last_run) )

    # Restore saved last_run states
    async def Restore( self ) -> None:
        last_run = await RD.get( f"{self.__type__}_{self.__name__}_{self.__user__}" )
        if last_run:
            self.last_run = ujson.loads( last_run )

    #

    async def GetRunning( self ) -> int:
        return self.running

    async def GetWaiting( self ) -> int:
        return self.waiting

    #

    # Check site/group can start task by running tasks limit and last run time
    async def CanStart(
        self,
        proxy: str = ''
    ) -> bool:
        try:
            config = QC.groups[ self.__name__ ] if 'group' == self.__type__ else QC.sites[ self.__name__ ]
        except:
            return False

        one_time_max = getattr( config, MAX_ONETIME ) # get maximum simultaneously running tasks by site/group limit
        one_time_base = getattr( config, getattr( ONETIME, self.__user__ ) ) # get maximum simultaneously running tasks by user limit
        delay = getattr( config, getattr( DELAY, self.__user__ ) ) # get maximum simultaneously running tasks by site/group/user limit

        by_max = True
        by_base = True
        by_last_run = True
        
        if one_time_max > 0:
            by_max: bool = ( self.running < one_time_max )

        if one_time_base > 0 and proxy in self.running_r:
            by_base = ( self.running_r[ proxy ] < one_time_base )

        if proxy in self.last_run:
            by_last_run = self.last_run[ proxy ] < ( datetime.now().timestamp() - delay )

        return by_max and by_base and by_last_run

    #

    # Check site/group can add task by user/site/group limit
    async def CanAdd( self ) -> bool:
        try:
            config = QC.groups[ self.__name__ ] if 'group' == self.__type__ else QC.sites[ self.__name__ ]
        except:
            return False

        waiting_base = getattr( config, getattr( WAIT, self.__user__ ) ) # get maximum simultaneously running tasks by site/group limit
        waiting_max = getattr( config, MAX_WAIT ) # get maximum simultaneously running tasks by user limit

        by_max = True
        by_base = True

        if waiting_max > 0:
            by_max: bool = ( self.waiting < waiting_max )

        if waiting_base > 0:
            by_base: bool = ( self.waiting < waiting_base )
    
        return by_base and by_max

    #

    # Increase running tasks count
    async def AddRun(
        self,
        proxy: str = ''
    ) -> None:
        if proxy not in self.running_r:
            self.running_r[ proxy ] = 0

        self.running_r[ proxy ] += 1

        self.running += 1
        self.last_run[ proxy ] = datetime.now().timestamp()

    # Decrease running tasks count
    async def RemoveRun(
        self,
        proxy: str = ''
    ) -> None:
        if proxy not in self.running_r:
            self.running_r[ proxy ] = 0

        self.running_r[ proxy ] = self.running_r[ proxy ]-1

        if self.running_r[ proxy ] <= 0:
            del self.running_r[ proxy ]

        self.running = self.running-1 if self.running > 1 else 0
        self.last_run[ proxy ] = datetime.now().timestamp()

    #

    # Increase waiting tasks count
    async def AddWaiting( self ) -> None:
        self.waiting += 1

    # Decrease waiting tasks count
    async def RemoveWaiting( self ) -> None:
        self.waiting -= 1
        if self.waiting < 0:
            self.waiting = 0