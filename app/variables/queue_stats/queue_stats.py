from __future__ import annotations

from typing import List, Dict
from typing import overload

from .queue_stats_user import QueueStatsUser
from .queue_stats_root import QueueStatsRoot, NONE_USER

class QueueStats( QueueStatsRoot ):
    users: Dict[ int, QueueStatsUser ] = {}

    def __repr__( self ) -> str:
        return '<QueueStats '+str( {
            'groups': self.groups,
            'sites':  self.sites,
            'users':  self.users,
        } )+'>'
    
    def __init__( self ) -> None:
        self.__type__= 'root'
        self.__user__= NONE_USER
        self.groups =  {}
        self.sites =   {}
        self.users =   {}
    
    async def Export( self ) -> Dict[ str, Dict [ str, int ] ]:
        result = {
            'sites': {},
            'groups': {},
        }

        for site_name in self.sites.keys():
            result[ 'sites' ][ site_name ] = await self.sites[ site_name ].GetRunning()

        for group_name in self.groups.keys():
            result[ 'groups' ][ group_name ] = await self.groups[ group_name ].GetRunning()
        return result


    # Remove expired users from statistic
    async def Flush( self ) -> None:
        for id in list( self.users.keys() ):
            if await self.users[ id ].Expired():
                await self.UserDestroy( id )
        await self.Save()

    # Save last_run states
    async def Save( self ) -> None:
        for site_name in self.sites.keys():
            await self.sites[ site_name ].Save()

        for group_name in self.groups.keys():
            await self.groups[ group_name ].Save()

        for id in self.users.keys():
            await self.users[ id ].Save()

    #

    # Get active groups names
    async def GetActiveGroups( self ) -> List[ str ]:
        return list( self.groups.keys() )

    # Get active sites names
    async def GetActiveSites( self ) -> List[ str ]:
        return list( self.sites.keys() )

    #

    # Add user to statistic
    async def UserInit(
        self,
        user_id: int
    ) -> bool:
        if user_id not in self.users:
            self.users[ user_id ] = QueueStatsUser( 'user', user_id )
            await self.users[ user_id ].Restore()
        return True

    # Remove user from statistic
    async def UserDestroy(
        self,
        user_id: int
    ) -> bool:
        ok: bool = user_id in self.users
        if ok:
            del self.users[ user_id ]
        return True

    # Check user exists in statistic
    async def UserExists(
        self,
        user_id: int
    ) -> bool:
        ok: bool = user_id in self.users
        return ok

    #

    # Check user can add task ( have free spots in waiting queue )
    async def UserCanAdd(
        self,
        user_id: int,
        site_name: str,
        group_name: str
    ) -> bool:
        await self.UserInit( user_id )
        return await self.users[ user_id ].CanAdd( site_name, group_name )

    # Check user can start task ( have free spots in running queue )
    async def UserCanStart(
        self,
        user_id: int,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> bool:
        await self.UserInit( user_id )
        return await self.users[ user_id ].CanStart( site_name, group_name, proxy )
    
    #

    # Increase running tasks count
    async def UserAddRun(
        self,
        user_id: int,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].AddRun( site_name, group_name, proxy )

    # Decrease running tasks count
    async def UserRemoveRun(
        self,
        user_id: int,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].RemoveRun( site_name, group_name, proxy )
    
    #

    # Increase waiting tasks count
    async def UserAddWaiting(
        self,
        user_id: int,
        site_name: str,
        group_name: str
    ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].AddWaiting( site_name, group_name )

    # Decrease waiting tasks count
    async def UserRemoveWaiting(
        self,
        user_id: int,
        site_name: str,
        group_name: str
    ) -> None:
        await self.UserInit( user_id )
        await self.users[ user_id ].SiteInit( site_name )
        await self.users[ user_id ].GroupInit( group_name )
        await self.users[ user_id ].RemoveWaiting( site_name, group_name )
    
    #

    # overload
    # Increase running tasks count
    async def AddRun(
        self,
        user_id: int,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        await self.GroupAddRun( group_name, proxy )
        await self.SiteAddRun( site_name, proxy )
        await self.UserAddRun( user_id, site_name, group_name, proxy )

    # overload
    # Decrease running tasks count
    async def RemoveRun(
        self,
        user_id: int,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        await self.GroupRemoveRun( group_name, proxy )
        await self.SiteRemoveRun( site_name, proxy )
        await self.UserRemoveRun( user_id, site_name, group_name, proxy )

    #

    # overload
    # Increase waiting tasks count
    async def AddWaiting(
        self,
        user_id: int,
        site_name: str,
        group_name: str
    ) -> None:
        await self.GroupAddWaiting( group_name )
        await self.SiteAddWaiting( site_name )
        await self.UserAddWaiting( user_id, site_name, group_name )

    # overload
    # Decrease waiting tasks count
    async def RemoveWaiting(
        self,
        user_id: int,
        site_name: str,
        group_name: str
    ) -> None:
        await self.GroupRemoveWaiting( group_name )
        await self.SiteRemoveWaiting( site_name )
        await self.UserRemoveWaiting( user_id, site_name, group_name )