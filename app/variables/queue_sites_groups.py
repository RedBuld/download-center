from __future__ import annotations
import ujson
from typing import List, Dict, Any
from datetime import datetime, timedelta

class QueueSitesGroups():
    map: Dict[ str, List[ str ] ] = {}

    def __init__(self) -> None:
        self.map = {}


    # Get all data
    async def GetAll( self ) -> Dict[ str, List[ str ] ]:
        return self.map


    # Get active sites
    async def GetActiveSites( self ) -> List[ str ]:
        return list( self.map.keys() )


    # Get all site groups
    async def GetSiteGroups(
        self,
        site_name: str
    ) -> List[ str ]:
        ok: bool = site_name in self.map
        if ok:
            return self.map[ site_name ]
        return []


    # Get site group by site and selected format
    async def GetSiteGroup(
        self,
        site_name: str,
        format: str
    ) -> str:
        from app.configs import QC
        ok: bool = site_name in self.map
        if ok:
            groups = self.map[ site_name ]
            for group_name in groups:
                if format in QC.groups[ group_name ].formats:
                    return group_name
        return ""


    # Add site to mapping
    async def SiteInit(
        self,
        site_name: str,
        site_groups: List[ str ]
    ) -> bool:
        self.map[ site_name ] = site_groups
        return True


    # Remove site from mapping
    async def SiteDestroy(
        self,
        site_name: str
    ) -> bool:
        ok: bool = site_name in self.map
        if ok:
            del self.map[ site_name ]
        return True