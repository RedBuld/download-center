from __future__ import annotations

import ujson
from typing import Dict

from app.objects import RD

from .queue_stats_obj import QueueStatsObj
from .queue_stats_root import QueueStatsRoot

class QueueStatsUser( QueueStatsRoot ):
    sites:     Dict[ str, QueueStatsObj ] = {}
    groups:    Dict[ str, QueueStatsObj ] = {}
    
    def __init__(
            self,
            __type__:  str,
            __user__:  int
        ) -> None:
        self.__type__        = 'user'
        self.__user__        = str( __user__ )
        self.groups          = {}
        self.sites           = {}
        self.default_can_add = True
        self.default_can_run = True


    def __repr__( self ) -> str:
        return '<QueueStatsUser ' + str( {
            'groups': self.groups,
            'sites': self.sites,
        } ) + '>'

    # Check user can be removed from stats
    async def Expired( self ) -> bool:
        all_groups_free = True
        all_sites_free = True

        for group_name in self.groups.keys():
            # Check group has no tasks and last_run marker expired
            tasks_empty = await self.GroupNotBusy( group_name )
            last_run_expired = await self.GroupCanStart( group_name )
            if not tasks_empty or not last_run_expired:
                all_groups_free = False
                break

        for site_name in self.sites.keys():
            # Check site has no tasks and last_run marker expired
            tasks_empty = await self.SiteNotBusy( site_name )
            last_run_expired = await self.SiteCanStart( site_name )
            if not tasks_empty or not last_run_expired:
                all_sites_free = False
                break

        return all_groups_free and all_sites_free

    # Save last_run states
    async def Save( self ) -> None:
        await RD.setex( f"{self.__type__}_{self.__user__}_sites", 3600, ujson.dumps( list( self.sites.keys() ) ) )
        await RD.setex( f"{self.__type__}_{self.__user__}_groups", 3600, ujson.dumps( list( self.groups.keys() ) ) )

        for site_name in self.sites.keys():
            await self.sites[ site_name ].Save()

        for group_name in self.groups.keys():
            await self.groups[ group_name ].Save()

    # Restore saved last_run states
    async def Restore( self ) -> None:
        sites = await RD.get( f"{self.__type__}_{self.__user__}_sites" )
        groups = await RD.get( f"{self.__type__}_{self.__user__}_groups" )

        if sites:
            site_names: list = ujson.loads( sites )
            for site_name in site_names:
                await self.SiteInit( site_name )

        if groups:
            group_names: list = ujson.loads( groups )
            for group_name in group_names:
                await self.GroupInit( group_name )

