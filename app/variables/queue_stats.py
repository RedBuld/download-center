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
    last_run:  datetime = datetime(1970,1,1)

    def __init__(
            self,
            __type__:  str,
            __name__:  str,
            active:    int = 0,
            last_run:  datetime = datetime(1970,1,1),
        ):
        self.__type__ =  __type__
        self.__name__ =  __name__
        self.active =    active
        self.last_run =  last_run

    def __repr__( self ) -> str:
        return '<QueueStatsObj '+str( {
            '__type__': self.__type__,
            '__name__': self.__name__,
            'active':   self.active,
            'last_run': self.last_run,
        } )+'>'

    async def Restore(self):
        last_run = await RD.get( f"{self.__type__}_{self.__name__}" )
        if last_run:
            self.last_run = datetime.fromtimestamp( float( last_run ) )

    async def Save(self):
        await RD.setex( f"{self.__type__}_{self.__name__}", 3600, self.last_run.timestamp() )

    async def CanStart( self, simultaneously: int, delay: int ) -> bool:
        simultaneously_limit: bool = ( self.active < simultaneously ) if simultaneously > 0 else True
        last_run_limit: bool = self.last_run < ( datetime.now() - timedelta( seconds=delay ) )
        return simultaneously_limit and last_run_limit

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

class QueueStatsUser():
    __type__:  str
    __id__:    int
    sites:     Dict[ str, QueueStatsObj ] = {}
    groups:    Dict[ str, QueueStatsObj ] = {}
    
    def __init__(
            self,
            __type__:  str,
            __id__:    int
        ) -> None:
        self.__type__ =  __type__
        self.__id__ =    __id__
        self.groups =    {}
        self.sites =     {}

    def __repr__( self ) -> str:
        return '<QueueStatsUser '+str( {
            'groups': self.groups,
            'sites': self.sites,
        } )+'>'

    async def Staled(self) -> bool:
        all_groups_staled = True
        all_sites_staled = True
        for group_name in self.groups.keys():
            if not await self.GroupNotRunning(group_name) or not await self.GroupCanStart(group_name):
                all_groups_staled = False
                break
        for site_name in self.sites.keys():
            if not await self.SiteNotRunning(site_name) or not await self.SiteCanStart(site_name):
                all_sites_staled = False
                break
        return all_groups_staled and all_sites_staled

    async def Restore(self):
        sites = await RD.get( f"{self.__type__}_{self.__id__}_sites" )
        groups = await RD.get( f"{self.__type__}_{self.__id__}_groups" )
        if sites:
            site_names: list = ujson.loads( sites )
            for site_name in site_names:
                self.sites[ site_name ] = QueueStatsObj( f'{self.__type__}_{self.__id__}_site', site_name )
                await self.sites[ site_name ].Restore()
        if groups:
            group_names: list = ujson.loads( groups )
            for group_name in group_names:
                self.groups[ group_name ] = QueueStatsObj( f'{self.__type__}_{self.__id__}_group', group_name )
                await self.groups[ group_name ].Restore()

    async def Save(self):
        await RD.setex( f"{self.__type__}_{self.__id__}_sites", 3600, ujson.dumps( list( self.sites.keys() ) ) )
        await RD.setex( f"{self.__type__}_{self.__id__}_groups", 3600, ujson.dumps( list( self.groups.keys() ) ) )
        for site_name in self.sites.keys():
            await self.sites[ site_name ].Save()
        for group_name in self.groups.keys():
            await self.groups[ group_name ].Save()

    #

    async def GroupInit( self, group_name: str ) -> bool:
        self.groups[ group_name ] = QueueStatsObj( 'group', group_name )
        await self.groups[ group_name ].Restore()
        return True

    async def SiteInit( self, site_name: str ) -> bool:
        self.sites[ site_name ] = QueueStatsObj( 'site', site_name )
        await self.sites[ site_name ].Restore()
        return True
    
    #

    async def CanStart( self, site_name: str, group_name: str ) -> bool:
        group_can_start: bool = await self.GroupCanStart( group_name )
        site_can_start: bool = await self.SiteCanStart( site_name )
        return group_can_start and site_can_start

    async def GroupCanStart( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanStart( QC.groups[ group_name ].simultaneously, QC.groups[ group_name ].delay_per_user )
        return True

    async def SiteCanStart( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanStart( QC.sites[ site_name ].simultaneously, QC.sites[ site_name ].delay_per_user )
        return True
    
    #
    
    async def GroupNotRunning( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return self.groups[ group_name ].active == 0
        return True

    async def SiteNotRunning( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return self.sites[ site_name ].active == 0
        return True

    #

    async def AddRun( self, site_name: str, group_name: str ) -> bool:
        await self.GroupAddRun( group_name )
        await self.SiteAddRun( site_name )
        return True
    
    async def GroupAddRun( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if not ok:
            await self.GroupInit( group_name )
        await self.groups[ group_name ].AddRun()
        return True

    async def SiteAddRun( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if not ok:
            await self.SiteInit( site_name )
        await self.sites[ site_name ].AddRun()
        return True

    #

    async def RemoveRun( self, site_name: str, group_name: str ) -> bool:
        await self.GroupRemoveRun( group_name )
        await self.SiteRemoveRun( site_name )
        return True

    async def GroupRemoveRun( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].RemoveRun()
        return ok

    async def SiteRemoveRun( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].RemoveRun()
        return ok

class QueueStats():
    groups: Dict[str,QueueStatsObj]  = {}
    sites:  Dict[str,QueueStatsObj]  = {}
    users:  Dict[int,QueueStatsUser] = {}

    def __repr__( self ) -> str:
        return '<QueueStats '+str( {
            'groups': self.groups,
            'sites':  self.sites,
            'users':  self.users,
        } )+'>'
    
    def __init__( self ) -> None:
        self.groups = {}
        self.sites =  {}
        self.users =  {}
    
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
        print('Doing flush')
        for user_id in list(self.users.keys()):
            if await self.users[ user_id ].Staled():
                await self.UserDestroy( user_id )
        await self.Save()

    async def Save(self):
        print('Doing save')
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

    async def GroupInit( self, group_name: str ) -> bool:
        if group_name not in self.groups:
            self.groups[ group_name ] = QueueStatsObj( 'group', group_name )
            await self.groups[ group_name ].Restore()
        return True

    async def SiteInit( self, site_name: str ) -> bool:
        if site_name not in self.sites:
            self.sites[ site_name ] = QueueStatsObj( 'site', site_name )
            await self.sites[ site_name ].Restore()
        return True

    async def UserInit( self, user_id: int ) -> bool:
        if user_id not in self.users:
            self.users[ user_id ] = QueueStatsUser( 'user', user_id )
            await self.users[ user_id ].Restore()
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

    async def UserDestroy( self, user_id: int ) -> bool:
        ok: bool = user_id in self.users
        if ok:
            del self.users[ user_id ]
        return True

    #

    async def GroupExists( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        return ok

    async def SiteExists( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        return ok

    async def UserExists( self, user_id: int ) -> bool:
        ok: bool = user_id in self.users
        return ok

    #

    async def GroupCanStart( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanStart( QC.groups[ group_name ].simultaneously, QC.groups[ group_name ].delay )
        return False

    async def SiteCanStart( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanStart( QC.sites[ site_name ].simultaneously, QC.sites[ site_name ].delay )
        return False

    async def UserCanStart( self, user_id: int, site_name: str, group_name: str ) -> bool:
        ok: bool = user_id in self.users
        if not ok:
            await self.UserInit( user_id )
        return await self.users[ user_id ].CanStart( site_name, group_name )

    #

    async def GroupAddRun( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].AddRun()
        return ok

    async def SiteAddRun( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].AddRun()
        return ok
    
    async def UserAddRun( self, user_id: int, site_name: str, group_name: str ) -> bool:
        if not await self.UserExists( user_id ):
            await self.UserInit( user_id )
        # await self.GroupAddRun( group_name )
        # await self.SiteAddRun( group_name )
        await self.users[ user_id ].AddRun( site_name, group_name )
        return

    #

    async def GroupRemoveRun( self, group_name: str ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].RemoveRun()
        return ok

    async def SiteRemoveRun( self, site_name: str ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].RemoveRun()
        return ok
    
    async def UserRemoveRun( self, user_id: int, site_name: str, group_name: str ) -> bool:
        if not await self.UserExists( user_id ):
            await self.UserInit( user_id )
        # await self.GroupRemoveRun( group_name )
        # await self.SiteRemoveRun( group_name )
        return await self.users[ user_id ].RemoveRun( site_name, group_name )