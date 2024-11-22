from __future__ import annotations
import os
import ujson
import traceback
from typing import Dict, Any


class GlobalConfig():
    bot_host:    str
    queue_host:  str
    inited:      bool = False

    async def updateConfig( self ):
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

        self.bot_host = config['bot_host'] if 'bot_host' in config else ''
        self.queue_host = config['queue_host'] if 'queue_host' in config else ''