from __future__ import annotations
import os
import ujson
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from dacite import from_dict, Config
from typing import Callable, Optional, List, Dict, Any
from app import models

class QueueConfig():
    formats_params:     Dict[ str, List[ str ] ]
    proxies:            QueueConfigProxies
    groups:             Dict[ str, QueueConfigGroup ]
    sites:              Dict[ str, QueueConfigSite ]
    inited:             bool = False

    def __init__(self):
        self.formats_params = None
        self.proxies = None
        self.groups = None
        self.sites = None
        self.inited = False

    def __repr__(self):
        return 'QC:'+str({
            'formats_params': self.formats_params,
            'groups': self.groups,
            'sites': self.sites,
        })

    async def updateConfig(
        self
    ):
        config_path = []

        cwd = os.getcwd()

        config_path.append(cwd)

        if not cwd.endswith('app/') and not cwd.endswith('app'):
            config_path.append('app')

        config_file = os.path.join( *config_path,  'configs', 'queue.json' )

        config: Dict[str,Any] = {}

        try:
            if not os.path.exists(config_file):
                raise FileNotFoundError(config_file)

            with open( config_file, 'r', encoding='utf-8' ) as _config_file:
                _config = _config_file.read()
                config = ujson.loads( _config )
        except Exception as e:
            if not self.inited:
                raise e
            traceback.print_exc()

        _formats_params = config['formats_params'] if 'formats_params' in config else {}
        formats_params = {}

        for format, format_params in _formats_params.items():
            formats_params[format] = format_params


        _groups = config['groups'] if 'groups' in config else {}
        groups = {}

        for group_name, group_data in _groups.items():
            groups[group_name] = from_dict(data_class=QueueConfigGroup, data=group_data, config=Config(check_types=False)) 


        _proxies = config['proxies'] if 'proxies' in config else []
        proxies = from_dict(data_class=QueueConfigProxies, data={'proxies':_proxies}, config=Config(check_types=False))

        _sites = config['sites'] if 'sites' in config else {}
        sites = {}

        for site_name, site_data in _sites.items():
            sites[site_name] = from_dict(data_class=QueueConfigSite, data=site_data, config=Config(check_types=False)) 

        self.formats_params = formats_params
        self.groups = groups
        self.sites = sites
        if self.proxies:
            proxies.last_by_site = self.proxies.last_by_site
        self.proxies = proxies


@dataclass
class QueueConfigGroup():
    per_user:           int = 1
    simultaneously:     int = 1
    max_simultaneously: int = 0
    delay:              int = 0
    delay_per_user:     int = 0
    waiting:            int = 0
    waiting_per_user:   int = 0
    formats:            List[ str ] = field(default_factory=list)
    downloader:         str = "elib2ebook"

    def __repr__(self):
        return str({
            'per_user':           self.per_user,
            'simultaneously':     self.simultaneously,
            'max_simultaneously': self.max_simultaneously,
            'delay':              self.delay,
            'delay_per_user':     self.delay_per_user,
            'waiting':            self.waiting,
            'waiting_per_user':   self.waiting_per_user,
            'formats':            self.formats,
            'downloader':         self.downloader,
        })

@dataclass
class QueueConfigSite():
    parameters:         List[ str ] = field(default_factory=list)
    formats:            List[ str ] = field(default_factory=list)
    downloader:         str = "elib2ebook"
    active:             bool = True
    use_proxy:          bool = False
    simultaneously:     int = 1
    max_simultaneously: int = 0
    per_user:           int = 1
    allowed_groups:     List[ str ] = field(default_factory=list)
    delay:              int = 0
    delay_per_user:     int = 0
    waiting:            int = 0
    waiting_per_user:   int = 0
    page_delay:         int = 0

    def __repr__(self):
        return str({
            'parameters':         self.parameters,
            'formats':            self.formats,
            'downloader':         self.downloader,
            'active':             self.active,
            'use_proxy':          self.use_proxy,
            'simultaneously':     self.simultaneously,
            'max_simultaneously': self.max_simultaneously,
            'per_user':           self.per_user,
            'allowed_groups':     self.allowed_groups,
            'delay':              self.delay,
            'delay_per_user':     self.delay_per_user,
            'waiting':            self.waiting,
            'waiting_per_user':   self.waiting_per_user,
            'page_delay':         self.page_delay,
        })

@dataclass(init=False)
class QueueConfigProxies():
    proxies: List[ str ] = field(default_factory=list)

    last_by_site: Dict[str, int] = field(default_factory=dict)

    def __init__(self, proxies: List[ str ], last_by_site: Dict[str, int] = {} ) -> None:
        self.proxies = proxies
        self.last_by_site = last_by_site
    
    def has(self) -> bool:
        return len(self.proxies) != 0

    async def getProxy(self, site: str) -> str:
        index = 0

        if len(self.proxies) == 0:
            return ''
        
        if site in self.last_by_site:
            index = self.last_by_site[ site ]
            index += 1
            if index > len(self.proxies) - 1:
                index = 0

        self.last_by_site[ site ] = index
        return self.proxies[ index ]
