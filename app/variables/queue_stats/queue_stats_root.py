from __future__ import annotations

from typing import List, Dict, Any

from datetime import datetime, timedelta

from .queue_stats_obj import QueueStatsObj, NONE_USER

class QueueStatsRoot():
    __type__:        str = ''
    __user__:        str = NONE_USER
    groups:          Dict[ str, QueueStatsObj ]  = {}
    sites:           Dict[ str, QueueStatsObj ]  = {}
    default_can_add: bool = False
    default_can_run: bool = False


    def __init__( self ) -> None:
        self.__type__ = 'root'
        self.__user__ = NONE_USER
        self.groups   = {}
        self.sites    = {}
        self.users    = {}

    #

    # Add group to statistic
    async def GroupInit(
        self,
        group_name: str
    ) -> bool:
        if group_name not in self.groups:
            self.groups[ group_name ] = QueueStatsObj( 'group', group_name, self.__user__ )
            await self.groups[ group_name ].Restore()
        return True

    # Remove group from statistic
    async def GroupDestroy(
        self,
        group_name: str
    ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            del self.groups[ group_name ]
        return True

    # Check group exists in statistic
    async def GroupExists(
        self,
        group_name: str
    ) -> bool:
        ok: bool = group_name in self.groups
        return ok

    #

    # Add site to in statistic
    async def SiteInit(
        self,
        site_name: str
    ) -> bool:
        if site_name not in self.sites:
            self.sites[ site_name ] = QueueStatsObj( 'site', site_name, self.__user__ )
            await self.sites[ site_name ].Restore()
        return True

    # Remove site from in statistic
    async def SiteDestroy(
        self,
        site_name: str
    ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            del self.sites[ site_name ]
        return True

    # Check site exists in statistic
    async def SiteExists(
        self,
        site_name: str
    ) -> bool:
        ok: bool = site_name in self.sites
        return ok

    #

    # Check group and site can add task ( have free spots in waiting queue )
    async def CanAdd(
        self,
        site_name: str,
        group_name: str
    ) -> bool:
        group_can = await self.GroupCanAdd( group_name )
        site_can = await self.SiteCanAdd( site_name )
        return group_can and site_can

    # Check group can add task ( have free spots in waiting queue )
    async def GroupCanAdd(
        self,
        group_name: str
    ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanAdd()
        return self.default_can_add

    # Check site can add task ( have free spots in waiting queue )
    async def SiteCanAdd(
        self,
        site_name: str
    ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanAdd()
        return self.default_can_add

    #

    # Check group and site can start task ( have free spots in running queue )
    async def CanStart(
        self,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        group_can = await self.GroupCanStart( group_name, proxy )
        site_can = await self.SiteCanStart( site_name, proxy )
        return group_can and site_can

    # Check group can start task ( have free spots in running queue )
    async def GroupCanStart(
        self,
        group_name: str,
        proxy: str = ''
    ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            return await self.groups[ group_name ].CanStart( proxy )
        return self.default_can_run

    # Check site can start task ( have free spots in running queue )
    async def SiteCanStart(
        self,
        site_name: str,
        proxy: str = ''
    ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            return await self.sites[ site_name ].CanStart( proxy )
        return self.default_can_run

    #

    # Increase running tasks count
    async def AddRun(
        self,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        await self.GroupAddRun( group_name, proxy )
        await self.SiteAddRun( site_name, proxy )

    # Increase running tasks count by group
    async def GroupAddRun(
        self,
        group_name: str,
        proxy: str = ''
    ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].AddRun( proxy )

    # Increase running tasks count by site
    async def SiteAddRun(
        self,
        site_name: str,
        proxy: str = ''
    ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].AddRun( proxy )

    #

    # Decrease running tasks count
    async def RemoveRun(
        self,
        site_name: str,
        group_name: str,
        proxy: str = ''
    ) -> None:
        await self.GroupRemoveRun( group_name, proxy )
        await self.SiteRemoveRun( site_name, proxy )

    # Decrease running tasks count from group
    async def GroupRemoveRun(
        self,
        group_name: str,
        proxy: str = ''
    ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].RemoveRun( proxy )

    # Decrease running tasks count from site
    async def SiteRemoveRun(
        self,
        site_name: str,
        proxy: str = ''
    ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].RemoveRun( proxy )

    #

    # Increase waiting tasks count
    async def AddWaiting(
        self,
        site_name: str,
        group_name: str
    ) -> None:
        await self.GroupAddWaiting( group_name )
        await self.SiteAddWaiting( site_name )

    # Increase waiting tasks count by group
    async def GroupAddWaiting(
        self,
        group_name: str
    ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].AddWaiting()

    # Increase waiting tasks count by site
    async def SiteAddWaiting(
        self,
        site_name: str
    ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].AddWaiting()

    #

    # Decrease waiting tasks count
    async def RemoveWaiting(
        self,
        site_name: str,
        group_name: str
    ) -> None:
        await self.GroupRemoveWaiting( group_name )
        await self.SiteRemoveWaiting( site_name )

    # Decrease waiting tasks count from group
    async def GroupRemoveWaiting(
        self,
        group_name: str
    ) -> None:
        ok: bool = group_name in self.groups
        if ok:
            await self.groups[ group_name ].RemoveWaiting()
        return

    # Decrease waiting tasks count from site
    async def SiteRemoveWaiting(
        self,
        site_name: str
    ) -> None:
        ok: bool = site_name in self.sites
        if ok:
            await self.sites[ site_name ].RemoveWaiting()
    
    #
    
    # Check 
    async def GroupNotBusy(
        self,
        group_name: str
    ) -> bool:
        ok: bool = group_name in self.groups
        if ok:
            running_count = await self.groups[ group_name ].GetRunning()
            waiting_count = await self.groups[ group_name ].GetWaiting()
            return running_count == 0 and waiting_count == 0
        return True

    async def SiteNotBusy(
        self,
        site_name: str
    ) -> bool:
        ok: bool = site_name in self.sites
        if ok:
            running_count = await self.sites[ site_name ].GetRunning()
            waiting_count = await self.sites[ site_name ].GetWaiting()
            return running_count == 0 and waiting_count == 0
        return True