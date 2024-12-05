from __future__ import annotations
import ujson
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.objects import RD
from app.configs import QC

class QueueStatsObj():
    __type__:  str
    __name__:  str
    active_t:  int = 0 # active total
    active_r:  int = 0 # active raw (no proxy)
    active_p:  Dict[str,int] = {} # active with proxy
    waiting:   int = 0
    last_run:  Dict[str, float] = {}

    def __init__(
            self,
            __type__:  str,
            __name__:  str
        ):
        self.__type__ =  __type__
        self.__name__ =  __name__
        self.active_t =  0
        self.active_r =  0
        self.active_p =  {}
        self.waiting =   0
        self.last_run =  {}

    @property
    def __json__( self ) -> str:
        return {
            '__type__': self.__type__,
            '__name__': self.__name__,
            'active_t': self.active_t,
            'active_r': self.active_r,
            'active_p': self.active_p,
            'waiting':  self.waiting,
            'last_run': self.last_run,
        }
    def __repr__( self ) -> str:
        return '<QueueStatsObj '+str( self.__json__ )+'>'

    async def Restore(self):
        last_run = await RD.get( f"{self.__type__}_{self.__name__}" )
        if last_run:
            self.last_run = ujson.loads( last_run )

    async def Save(self):
        await RD.setex( f"{self.__type__}_{self.__name__}", 3600, ujson.dumps(self.last_run) )

    async def CanStart( self, obj_name: str, simultaneously_key: str, delay_key: str, proxy: str = '' ) -> bool:
        source = QC.groups if 'group' in self.__type__ else QC.sites

        max_simultaneously = getattr( source[ obj_name ], 'max_simultaneously' )
        simultaneously = getattr( source[ obj_name ], simultaneously_key )
        delay = getattr( source[ obj_name ], delay_key )
        
        by_sim_total: bool = ( self.active_t < max_simultaneously ) if max_simultaneously > 0 else True

        if proxy:
            by_sim_single: bool = ( self.active_p[ proxy ] < simultaneously ) if ( simultaneously > 0 and proxy in self.active_p ) else True
        else:
            by_sim_single: bool = ( self.active_r < simultaneously ) if simultaneously > 0 else True

        by_last_run: bool = self.last_run[ proxy ] < ( datetime.now().timestamp() - delay ) if proxy in self.last_run else True
        return by_sim_total and by_sim_single and by_last_run

    async def CanAdd( self, waiting: int) -> bool:
        can: bool = ( self.waiting < waiting ) if waiting > 0 else True
        return can

    async def AddRun( self, proxy: str = '' ) -> bool:
        if proxy:
            if proxy not in self.active_p:
                self.active_p[ proxy ] = 0
            self.active_p[ proxy ] += 1
        else:
            self.active_r += 1
        self.active_t += 1
        self.last_run[ proxy ] = datetime.now().timestamp()
        return True

    async def RemoveRun( self, proxy: str = '' ) -> bool:
        if proxy:
            self.active_p[ proxy ] = self.active_p[ proxy ]-1
            if self.active_p[ proxy ] <= 0:
                del self.active_p[ proxy ]
        else:
            self.active_r = self.active_r-1 if self.active_r > 1 else 0
        self.active_t = self.active_t-1 if self.active_t > 1 else 0
        self.last_run[ proxy ] = datetime.now().timestamp()
        return True

    async def AddWaiting( self ) -> bool:
        self.waiting += 1
        return True

    async def RemoveWaiting( self ) -> bool:
        self.waiting -= 1
        if self.waiting < 0:
            self.waiting = 0
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

    async def CanStart( self, site_name: str, group_name: str, proxy: str = '' ) -> None:
        group_can = await self.GroupCanStart( group_name, proxy )
        site_can = await self.SiteCanStart( site_name, proxy )
        return group_can and site_can

    async def GroupCanStart( self, group_name: str, proxy: str = '' ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanStart( group_name, self.simultaneously_key, self.delay_key, proxy )
        return self.def_can_run

    async def SiteCanStart( self, site_name: str, proxy: str = '' ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanStart( site_name, self.simultaneously_key, self.delay_key, proxy )
        return self.def_can_run

    #

    async def AddRun( self, site_name: str, group_name: str, proxy: str = '' ) -> None:
        await self.GroupAddRun( group_name, proxy )
        await self.SiteAddRun( site_name, proxy )

    async def GroupAddRun( self, group_name: str, proxy: str = '' ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].AddRun( proxy )

    async def SiteAddRun( self, site_name: str, proxy: str = '' ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].AddRun( proxy )

    #

    async def RemoveRun( self, site_name: str, group_name: str, proxy: str = '' ) -> None:
        await self.GroupRemoveRun( group_name, proxy )
        await self.SiteRemoveRun( site_name, proxy )

    async def GroupRemoveRun( self, group_name: str, proxy: str = '' ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].RemoveRun( proxy )

    async def SiteRemoveRun( self, site_name: str, proxy: str = '' ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].RemoveRun( proxy )
    
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
            return self.groups[ group_name ].active_t == 0 and self.groups[ group_name ].waiting == 0
        return True

    async def SiteNotBusy( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return self.sites[ site_name ].active_t == 0 and self.sites[ site_name ].waiting == 0
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
            result['sites'][site_name] = self.sites[ site_name ].active_t
        for group_name in self.groups.keys():
            result['groups'][group_name] = self.groups[ group_name ].active_t
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

    async def UserCanStart( self, user_id: int, site_name: str, group_name: str, proxy: str = '' ) -> bool:
        await self.UserInit( user_id )
        return await self.users[ user_id ].CanStart( site_name, group_name, proxy )
    
    #

    async def UserAddRun( self, user_id: int, site_name: str, group_name: str, proxy: str = '' ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].AddRun( site_name, group_name, proxy )

    async def UserRemoveRun( self, user_id: int, site_name: str, group_name: str, proxy: str = '' ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].RemoveRun( site_name, group_name, proxy )
    
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

    async def AddRun( self, user_id: int, site_name: str, group_name: str, proxy: str = '' ) -> None:
        await self.GroupAddRun( group_name, proxy )
        await self.SiteAddRun( site_name, proxy )
        await self.UserAddRun( user_id, site_name, group_name, proxy )

    async def RemoveRun( self, user_id: int, site_name: str, group_name: str, proxy: str = '' ) -> None:
        await self.GroupRemoveRun( group_name, proxy )
        await self.SiteRemoveRun( site_name, proxy )
        await self.UserRemoveRun( user_id, site_name, group_name, proxy )

    #

    async def AddWaiting( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.GroupAddWaiting( group_name )
        await self.SiteAddWaiting( site_name )
        await self.UserAddWaiting( user_id, site_name, group_name )

    async def RemoveWaiting( self, user_id: int, site_name: str, group_name: str ) -> None:
        await self.GroupRemoveWaiting( group_name )
        await self.SiteRemoveWaiting( site_name )
        await self.UserRemoveWaiting( user_id, site_name, group_name )