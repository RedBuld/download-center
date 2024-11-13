from __future__ import annotations
import os
import ujson
import traceback
from dataclasses import dataclass
from typing import List, Dict, Any

class DownloaderConfig():
    save_folder:   str | os.PathLike
    exec_folder:   str | os.PathLike
    temp_folder:   str | os.PathLike
    compression:   Dict[ str, str | os.PathLike ]
    downloaders:   Dict[ str, DownloaderConfigExec ]

    def __repr__(self):
        return str({
            'save_folder': self.save_folder,
            'exec_folder': self.exec_folder,
            'temp_folder': self.temp_folder,
            'compression': self.compression,
            'downloaders': self.downloaders,
        })

    def __init__( self, **kwargs ) -> None:
        if 'save_folder' in kwargs:
            self.save_folder = kwargs['save_folder']
        if 'exec_folder' in kwargs:
            self.exec_folder = kwargs['exec_folder']
        if 'temp_folder' in kwargs:
            self.temp_folder = kwargs['temp_folder']
        if 'compression' in kwargs:
            self.compression = kwargs['compression']
        if 'downloaders' in kwargs:
            self.downloaders = kwargs['downloaders']

    async def updateConfig(
        self
    ):
        config_file = os.path.join( os.getcwd(), 'app', 'configs', 'downloader.json' )

        config: Dict[str,Any] = {}

        try:
            if not os.path.exists(config_file):
                raise FileNotFoundError(config_file)

            with open( config_file, 'r', encoding='utf-8' ) as _config_file:
                _config = _config_file.read()
                config = ujson.loads( _config )
        except:
            traceback.print_exc()

        self.save_folder = config['save_folder'] if 'save_folder' in config else ''
        self.exec_folder = config['exec_folder'] if 'exec_folder' in config else ''
        self.temp_folder = config['temp_folder'] if 'temp_folder' in config else ''
        self.compression = config['compression'] if 'compression' in config else {}
        _downloaders = config['downloaders'] if 'downloaders' in config else {}
        downloaders = {}

        for name, data in _downloaders.items():
            downloader = DownloaderConfigExec(**data)
            downloaders[name] = downloader

        self.downloaders = downloaders

@dataclass
class DownloaderConfigExec():
    folder:        str
    exec:          str

    def __repr__(self):
        return str({
            'folder': self.folder,
            'exec': self.exec,
        })

@dataclass
class DownloaderContext():
    save_folder:   str | os.PathLike
    exec_folder:   str | os.PathLike
    temp_folder:   str | os.PathLike
    compression:   Dict[ str, str | os.PathLike ]
    downloader:    DownloaderConfigExec