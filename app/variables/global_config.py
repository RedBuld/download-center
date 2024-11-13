from __future__ import annotations
import os
import ujson
import traceback
from typing import Dict, Any


class GlobalConfig():
    bot_host:    str
    queue_host:  str

    def __repr__(self):
        return str({
            'bot_host': self.bot_host,
            'queue_host': self.queue_host,
        })

    def __init__( self, **kwargs ) -> None:
        if 'bot_host' in kwargs:
            self.bot_host = kwargs['bot_host']
        if 'queue_host' in kwargs:
            self.queue_host = kwargs['queue_host']

    async def updateConfig(
        self
    ):
        config_file = os.path.join( os.getcwd(), 'app', 'configs', 'global.json' )

        config: Dict[str,Any] = {}

        try:
            if not os.path.exists(config_file):
                raise FileNotFoundError(config_file)

            with open( config_file, 'r', encoding='utf-8' ) as _config_file:
                _config = _config_file.read()
                config = ujson.loads( _config )
        except:
            traceback.print_exc()

        self.bot_host = config['bot_host'] if 'bot_host' in config else ''
        self.queue_host = config['queue_host'] if 'queue_host' in config else ''