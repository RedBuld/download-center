from __future__ import annotations
import os
import ujson
import traceback
from typing import Dict, Any


class GlobalConfig():
    bot_host:      str
    queue_host:    str
    flaresolverr:  str
    redis_server:  str
    restore_tasks: bool = True
    inited:        bool = False

    def __init__( self ):
        config_path = []

        cwd = os.getcwd()

        config_path.append(cwd)

        if not cwd.endswith('app/') and not cwd.endswith('app'):
            config_path.append('app')

        config_file = os.path.join( *config_path, 'configs', 'global.json' )

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
        

        if 'bot_host' in config:
            self.bot_host = config['bot_host']
        else:
            raise Exception('No bot_host defined')

        if 'queue_host' in config:
            self.queue_host = config['queue_host']
        else:
            raise Exception('No queue_host defined')

        if 'redis_server' in config:
            self.redis_server = config['redis_server']
        else:
            raise Exception('No redis_server defined')

        if 'flaresolverr' in config:
            self.flaresolverr = config['flaresolverr']
        else:
            self.flaresolverr = ''

        if 'restore_tasks' in config:
            self.restore_tasks = config['restore_tasks']
        else:
            self.restore_tasks = True

    async def updateConfig( self ):
        self.__init__()