from __future__ import annotations
import ujson
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.objects import RD
from app.configs import QC

class QueueStatsObj():
    __type__:  str
    __name__:  str
    active:    int = 0
    waiting:   int = 0
    last_run:  datetime = datetime(1970,1,1)

    def __init__(
            self,
            __type__:  str,
            __name__:  str,
            active:    int = 0,
            waiting:   int = 0,
            last_run:  datetime = datetime(1970,1,1),
        ):
        self.__type__ =  __type__
        self.__name__ =  __name__
        self.active =    active
        self.waiting =   waiting
        self.last_run =  last_run

    def __repr__( self ) -> str:
        return '<QueueStatsObj '+str( {
            '__type__': self.__type__,
            '__name__': self.__name__,
            'active':   self.active,
            'waiting':  self.waiting,
            'last_run': self.last_run,
        } )+'>'

    async def Restore(self):
        last_run = await RD.get( f"{self.__type__}_{self.__name__}" )
        if last_run:
            self.last_run = datetime.fromtimestamp( float( last_run ) )

    async def Save(self):
        await RD.setex( f"{self.__type__}_{self.__name__}", 3600, self.last_run.timestamp() )

    async def CanStart( self, simultaneously: int, delay: int ) -> bool:
        sim_can: bool = ( self.active < simultaneously ) if simultaneously > 0 else True
        lr_: bool = self.last_run < ( datetime.now() - timedelta( seconds=delay ) )
        return sim_can and lr_

    async def CanAdd( self, waiting: int) -> bool:
        can: bool = ( self.waiting < waiting ) if waiting > 0 else True
        return can

    async def AddRun( self ) -> bool:
        self.active += 1
        self.last_run = datetime.now()
        return True

    async def RemoveRun( self ) -> bool:
        self.active -= 1
        if self.active < 0:
            self.active = 0
        self.last_run = datetime.now()
        return True

    async def AddWaiting( self ) -> bool:
        self.waiting += 1
        self.last_run = datetime.now()
        return True

    async def RemoveWaiting( self ) -> bool:
        self.waiting -= 1
        if self.waiting < 0:
            self.waiting = 0
        self.last_run = datetime.now()
        return True

class QueueStatsRoot():
    __type__:           str = ''
    __name__:           str = ''
    groups:             Dict[str,QueueStatsObj]  = {}
    sites:              Dict[str,QueueStatsObj]  = {}
    delay_key:          str = 'delay'
    waiting_key:        str = 'waiting'
    simultaneously_key: str = 'simultaneously'
    def_can_add:        bool = False
    def_can_run:        bool = False
    
    def __init__( self ) -> None:
        self.__type__ =           ''
        self.__name__ =           ''
        self.groups =             {}
        self.sites =              {}
        self.users =              {}
        self.delay_key =          'delay'
        self.waiting_key =        'waiting'
        self.simultaneously_key = 'simultaneously'

    #

    async def GroupInit( self, group_name: str ) -> bool:
        if group_name not in self.groups:
            self.groups[ group_name ] = QueueStatsObj( f'{self.__type__}_{self.__name__}_group', group_name )
            await self.groups[ group_name ].Restore()
        return True

    async def SiteInit( self, site_name: str ) -> bool:
        if site_name not in self.sites:
            self.sites[ site_name ] = QueueStatsObj( f'{self.__type__}_{self.__name__}_site', site_name )
            await self.sites[ site_name ].Restore()
        return True

    #

    async def GroupDestroy( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            del self.groups[ group_name ]
        return True

    async def SiteDestroy( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            del self.sites[ site_name ]
        return True

    #

    async def GroupExists( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        return ok

    async def SiteExists( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        return ok

    #

    async def CanAdd( self, site_name: str, group_name: str ) -> bool:
        group_can = await self.GroupCanAdd( group_name )
        site_can = await self.SiteCanAdd( site_name )
        return group_can and site_can

    async def GroupCanAdd( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanAdd( getattr( QC.groups[ group_name ], self.waiting_key ) )
        return self.def_can_add

    async def SiteCanAdd( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanAdd( getattr( QC.sites[ site_name ], self.waiting_key ) )
        return self.def_can_add

    #

    async def CanStart( self, site_name: str, group_name: str ) -> None:
        group_can = await self.GroupCanStart( group_name )
        site_can = await self.SiteCanStart( site_name )
        return group_can and site_can

    async def GroupCanStart( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanStart( getattr( QC.groups[ group_name ], self.simultaneously_key ), getattr( QC.groups[ group_name ], self.delay_key ) )
        return self.def_can_run

    async def SiteCanStart( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanStart( getattr( QC.sites[ site_name ], self.simultaneously_key ), getattr( QC.sites[ site_name ], self.delay_key ) )
        return self.def_can_run

    #

    async def AddRun( self, site_name: str, group_name: str ) -> None:
        await self.GroupAddRun( group_name )
        await self.SiteAddRun( site_name )

    async def GroupAddRun( self, group_name: str ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].AddRun()

    async def SiteAddRun( self, site_name: str ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].AddRun()

    #

    async def RemoveRun( self, site_name: str, group_name: str ) -> None:
        await self.GroupRemoveRun( group_name )
        await self.SiteRemoveRun( site_name )

    async def GroupRemoveRun( self, group_name: str ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].RemoveRun()

    async def SiteRemoveRun( self, site_name: str ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].RemoveRun()
    
    #

    async def AddWaiting( self, site_name: str, group_name: str ) -> None:
        await self.GroupAddWaiting( group_name )
        await self.SiteAddWaiting( site_name )

    async def GroupAddWaiting( self, group_name: str ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].AddWaiting()

    async def SiteAddWaiting( self, site_name: str ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].AddWaiting()

    #

    async def RemoveWaiting( self, site_name: str, group_name: str ) -> None:
        await self.GroupRemoveWaiting( group_name )
        await self.SiteRemoveWaiting( site_name )

    async def GroupRemoveWaiting( self, group_name: str ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].RemoveWaiting()
        return

    async def SiteRemoveWaiting( self, site_name: str ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].RemoveWaiting()


class QueueStatsUser(QueueStatsRoot):
    sites:     Dict[ str, QueueStatsObj ] = {}
    groups:    Dict[ str, QueueStatsObj ] = {}
    
    def __init__(
            self,
            __type__:  str,
            __name__:    int
        ) -> None:
        self.__type__ =           __type__
        self.__name__ =           __name__
        self.groups =             {}
        self.sites =              {}
        self.delay_key =          'delay_per_user'
        self.waiting_key =        'waiting_per_user'
        self.simultaneously_key = 'per_user'
        self.def_can_add =        True
        self.def_can_run =        True

    def __repr__( self ) -> str:
        return '<QueueStatsUser '+str( {
            'groups': self.groups,
            'sites': self.sites,
        } )+'>'

    async def Staled(self) -> bool:
        all_groups = True
        all_sites = True
        for group_name in self.groups.keys():
            if not await self.GroupNotBusy(group_name) or not await self.GroupCanStart(group_name):
                all_groups = False
                break
        for site_name in self.sites.keys():
            if not await self.SiteNotBusy(site_name) or not await self.SiteCanStart(site_name):
                all_sites = False
                break
        return all_groups and all_sites

    async def Restore(self):
        sites = await RD.get( f"{self.__type__}_{self.__name__}_sites" )
        groups = await RD.get( f"{self.__type__}_{self.__name__}_groups" )
        if sites:
            site_names: list = ujson.loads( sites )
            for site_name in site_names:
                self.sites[ site_name ] = QueueStatsObj( f'{self.__type__}_{self.__name__}_site', site_name )
                await self.sites[ site_name ].Restore()
        if groups:
            group_names: list = ujson.loads( groups )
            for group_name in group_names:
                self.groups[ group_name ] = QueueStatsObj( f'{self.__type__}_{self.__name__}_group', group_name )
                await self.groups[ group_name ].Restore()

    async def Save(self):
        await RD.setex( f"{self.__type__}_{self.__name__}_sites", 3600, ujson.dumps( list( self.sites.keys() ) ) )
        await RD.setex( f"{self.__type__}_{self.__name__}_groups", 3600, ujson.dumps( list( self.groups.keys() ) ) )
        for site_name in self.sites.keys():
            await self.sites[ site_name ].Save()
        for group_name in self.groups.keys():
            await self.groups[ group_name ].Save()
    
    #
    
    async def GroupNotBusy( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return self.groups[ group_name ].active == 0 and self.groups[ group_name ].waiting == 0
        return True

    async def SiteNotBusy( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return self.sites[ site_name ].active == 0 and self.sites[ site_name ].waiting == 0
        return True

class QueueStats(QueueStatsRoot):
    users:  Dict[int,QueueStatsUser] = {}

    def __repr__( self ) -> str:
        return '<QueueStats '+str( {
            'groups': self.groups,
            'sites':  self.sites,
            'users':  self.users,
        } )+'>'
    
    def __init__( self ) -> None:
        self.__type__= 'root'
        self.__name__= ''
        self.groups =  {}
        self.sites =   {}
        self.users =   {}
    
    async def Export( self ) -> Dict[ str, Dict [ str, int ] ]:
        result = {
            'sites': {},
            'groups': {},
        }
        for site_name in self.sites.keys():
            result['sites'][site_name] = self.sites[ site_name ].active
        for group_name in self.groups.keys():
            result['groups'][group_name] = self.groups[ group_name ].active
        return result


    async def Flush( self ) -> None:
        for user_id in list(self.users.keys()):
            if await self.users[ user_id ].Staled():
                await self.UserDestroy( user_id )
        await self.Save()

    async def Save(self):
        for site_name in self.sites.keys():
            await self.sites[ site_name ].Save()
        for group_name in self.groups.keys():
            await self.groups[ group_name ].Save()
        for user_id in self.users.keys():
            await self.users[ user_id ].Save()

    #

    async def GetActiveGroups( self ) -> List[str]:
        return list( self.groups.keys() )

    async def GetActiveSites( self ) -> List[str]:
        return list( self.sites.keys() )

    #

    async def UserInit( self, user_id: int ) -> bool:
        if user_id not in self.users:
            self.users[ user_id ] = QueueStatsUser( 'user', user_id )
            await self.users[ user_id ].Restore()
        return True

    async def UserDestroy( self, user_id: int ) -> bool:
        ok: bool = user_id in self.users
        if ok:
            del self.users[ user_id ]
        return True

    async def UserExists( self, user_id: int ) -> bool:
        ok: bool = user_id in self.users
        return ok

    #

    async def UserCanAdd( self, user_id: int, site_name: str, group_name: str ) -> bool:
        await self.UserInit( user_id )
        return await self.users[ user_id ].CanAdd( site_name, group_name )

    async def UserCanStart( self, user_id: int, site_name: str, group_name: str ) -> bool:
        await self.UserInit( user_id )
        return await self.users[ user_id ].CanStart( site_name, group_name )
    
    #

    async def UserAddRun( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].AddRun( site_name, group_name )

    async def UserRemoveRun( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].RemoveRun( site_name, group_name )
    
    #

    async def UserAddWaiting( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].AddWaiting( site_name, group_name )

    async def UserRemoveWaiting( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].RemoveWaiting( site_name, group_name )
    
    #

    async def AddRun( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.GroupAddRun( group_name )
        await self.SiteAddRun( site_name )
        await self.UserAddRun( user_id, site_name, group_name )

    async def RemoveRun( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.GroupRemoveRun( group_name )
        await self.SiteRemoveRun( site_name )
        await self.UserRemoveRun( user_id, site_name, group_name )

    #

    async def AddWaiting( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.GroupAddWaiting( group_name )
        await self.SiteAddWaiting( site_name )
        await self.UserAddWaiting( user_id, site_name, group_name )

    async def RemoveWaiting( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.GroupRemoveWaiting( group_name )
        await self.SiteRemoveWaiting( site_name )
        await self.UserRemoveWaiting( user_id, site_name, group_name )