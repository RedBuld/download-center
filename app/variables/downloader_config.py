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
    arch_folder:   str | os.PathLike
    compression:   Dict[ str, str | os.PathLike ]
    downloaders:   Dict[ str, DownloaderConfigExec ]
    inited:        bool = False

    def __repr__(self):
        return 'DC:'+str({
            'save_folder': self.save_folder,
            'exec_folder': self.exec_folder,
            'temp_folder': self.temp_folder,
            'arch_folder': self.arch_folder,
            'compression': self.compression,
            'downloaders': self.downloaders,
        })

    async def updateConfig(
        self
    ):
        config_path = []

        cwd = os.getcwd()

        config_path.append(cwd)

        if not cwd.endswith('app/') and not cwd.endswith('app'):
            config_path.append('app')

        config_file = os.path.join( *config_path, 'configs', 'downloader.json' )

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

        if 'save_folder' in config:
            self.save_folder = config['save_folder']
        else:
            raise Exception('No save_folder in downloader.json config')
        if 'exec_folder' in config:
            self.exec_folder = config['exec_folder']
        else:
            raise Exception('No exec_folder in downloader.json config')
        if 'temp_folder' in config:
            self.temp_folder = config['temp_folder']
        else:
            raise Exception('No temp_folder in downloader.json config')
        if 'arch_folder' in config:
            self.arch_folder = config['arch_folder']
        else:
            raise Exception('No arch_folder in downloader.json config')
        
        if 'downloaders' in config:
            _downloaders = config['downloaders'] if 'downloaders' in config else {}
        else:
            raise Exception('No downloaders in downloader.json config')
        
        self.compression = config['compression'] if 'compression' in config else {}
        
        downloaders = {}
        for name, data in _downloaders.items():
            downloader = DownloaderConfigExec(**data)
            downloaders[name] = downloader

        self.downloaders = downloaders

        # print(self)

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
    arch_folder:   str | os.PathLike
    compression:   Dict[ str, Dict[ str, str | os.PathLike ] ]
    downloader:    DownloaderConfigExec
    page_delay:    int = 0