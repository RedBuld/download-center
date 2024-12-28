from __future__ import annotations
import os
import ujson
import traceback
from typing import Dict, Any


class GlobalConfig():
    bot_host:      str = 'http://bot:8000/'
    queue_host:    str = 'http://queue:8010/'
    redis_server:  str = 'redis://redis:6379/1'
    flaresolverr:  str
    restore_tasks: bool = True

    def __init__( self ) -> None:
        config_file = '/app/configs/global.json'
        if not os.path.exists( config_file ):
            raise FileNotFoundError( config_file )

        config: Dict[str,Any] = {}
        with open( config_file, 'r', encoding='utf-8' ) as _config_file:
            _config = _config_file.read()
            config = ujson.loads( _config )

        if 'flaresolverr' in config:
            self.flaresolverr = config['flaresolverr']
        else:
            self.flaresolverr = ''

        if 'restore_tasks' in config:
            self.restore_tasks = config['restore_tasks']
        else:
            self.restore_tasks = True


    async def UpdateConfig( self ) -> None:
        self.__init__()