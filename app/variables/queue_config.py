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
    groups:             Dict[ str, QueueConfigGroup ]
    groups:             Dict[ str, QueueConfigGroup ]
    sites:              Dict[ str, QueueConfigSite ]
    user_stats_timeout: int = 0
    Consumer:           Optional[ Callable[ [ models.DownloadResult ], None ] ] = None

    def __repr__(self):
        return str({
            'formats_params': self.formats_params,
            'groups': self.groups,
            'sites': self.sites,
            'user_stats_timeout': self.user_stats_timeout,
        })

    async def updateConfig(
        self
    ):
        queue_config_file = os.path.join( os.getcwd(), 'app', 'configs', 'queue.json' )

        config: Dict[str,Any] = {}

        try:
            if not os.path.exists(queue_config_file):
                raise FileNotFoundError(queue_config_file)

            with open( queue_config_file, 'r', encoding='utf-8' ) as _config_file:
                _config = _config_file.read()
                config = ujson.loads( _config )

                # print(_config)
                # config = from_dict(data_class=GlobalConfig, data=_config, config=Config(check_types=False))
                # print(config)
        except:
            traceback.print_exc()

        _formats_params = config['formats_params'] if 'formats_params' in config else {}
        formats_params = {}

        for format, format_params in _formats_params.items():
            formats_params[format] = format_params


        _groups = config['groups'] if 'groups' in config else {}
        groups = {}

        for group_name, group_data in _groups.items():
            groups[group_name] = from_dict(data_class=QueueConfigGroup, data=group_data, config=Config(check_types=False)) 


        _sites = config['sites'] if 'sites' in config else {}
        sites = {}

        for site_name, site_data in _sites.items():
            sites[site_name] = from_dict(data_class=QueueConfigSite, data=site_data, config=Config(check_types=False)) 

        self.formats_params = formats_params
        self.groups = groups
        self.sites = sites
        self.user_stats_timeout = int(config['user_stats_timeout']) if 'user_stats_timeout' in config else 0


@dataclass
class QueueConfigGroup():
    per_user:       int = 1
    simultaneously: int = 1
    delay:          int = 0
    delay_per_user: int = 0
    formats:        List[ str ] = field(default_factory=list)
    downloader:     str = "elib2ebook"

    def __repr__(self):
        return str({
            'per_user': self.per_user,
            'simultaneously': self.simultaneously,
            'delay': self.delay,
            'delay_per_user': self.delay_per_user,
            'formats': self.formats,
            'downloader': self.downloader,
        })

@dataclass
class QueueConfigSite():
    parameters:     List[ str ] = field(default_factory=list)
    formats:        List[ str ] = field(default_factory=list)
    downloader:     str = "elib2ebook"
    active:         bool = True
    proxy:          str = ""
    simultaneously: int = 1
    per_user:       int = 1
    allowed_groups: List[ str ] = field(default_factory=list)
    delay:          int = 0
    delay_per_user: int = 0
    pause_by_user:  int = 1

    def __repr__(self):
        return str({
            'parameters': self.parameters,
            'formats': self.formats,
            'downloader': self.downloader,
            'active': self.active,
            'proxy': self.proxy,
            'simultaneously': self.simultaneously,
            'per_user': self.per_user,
            'allowed_groups': self.allowed_groups,
            'delay': self.delay,
            'per_user': self.per_user,
            'pause_by_user': self.pause_by_user,
        })