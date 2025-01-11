from __future__ import annotations
import os
import ujson
from dataclasses import dataclass, field
from dacite import from_dict, Config
from typing import List, Dict, Any

class DownloaderConfig():
    save_folder: str | os.PathLike
    exec_folder: str | os.PathLike
    temp_folder: str | os.PathLike
    arch_folder: str | os.PathLike
    compression: Dict[ str, str | os.PathLike ]
    downloaders: Dict[ str, DownloaderConfigExec ]
    file_limit:  int = 1_549_000_000
    inited:      bool = False

    def __repr__( self ) -> str:
        return '<DownloaderConfig: ' + str( {
            'save_folder': self.save_folder,
            'exec_folder': self.exec_folder,
            'temp_folder': self.temp_folder,
            'arch_folder': self.arch_folder,
            'compression': self.compression,
        } ) + '>'

    async def UpdateConfig( self ) -> None:
        config_file = '/app/configs/downloader.json'
        if not os.path.exists( config_file ):
            raise FileNotFoundError( config_file )


        config: Dict[ str, Any ] = {}
        with open( config_file, 'r', encoding='utf-8' ) as _config_file:
            _config = _config_file.read()
            config = ujson.loads( _config )


        if 'save_folder' in config:
            self.save_folder = config[ 'save_folder' ]
        else:
            raise Exception('No save_folder in downloader.json config')


        if 'exec_folder' in config:
            self.exec_folder = config[ 'exec_folder' ]
        else:
            raise Exception('No exec_folder in downloader.json config')


        if 'temp_folder' in config:
            self.temp_folder = config[ 'temp_folder' ]
        else:
            raise Exception('No temp_folder in downloader.json config')


        if 'arch_folder' in config:
            self.arch_folder = config[ 'arch_folder' ]
        else:
            raise Exception('No arch_folder in downloader.json config')


        if 'downloaders' in config:
            _downloaders = config[ 'downloaders' ] if 'downloaders' in config else {}
        else:
            raise Exception('No downloaders in downloader.json config')


        self.compression = config[ 'compression' ] if 'compression' in config else {}


        self.file_limit = config[ 'file_limit' ] if 'file_limit' in config else 1_549_000_000

        if not os.environ.get('LOCAL_SERVER'):
            self.file_limit = 49_000_000


        downloaders = {}
        for name, data in _downloaders.items():
            downloaders[ name ] = from_dict( data_class=DownloaderConfigExec, data=data, config=Config( check_types=False ) ) 


        self.downloaders = downloaders


@dataclass()
class DownloaderConfigExec():
    folder:      str
    exec:        str
    clean:       List[ DownloaderConfigClean ] = field( default_factory=list )
    args:        Dict[ str, DownloaderConfigArg ] = field( default_factory=dict )
    format_args: Dict[ str, Dict[ str, DownloaderConfigFArg ] ] = field( default_factory=dict )

    # def __init__(
    #     self,
    #     folder: str = "",
    #     exec: str = "",
    #     clean: = ,
    #     args: = ,
    #     format_args: = ,
    # ) -> None:
    def __repr__( self ) -> str:
        return str( {
            'folder': self.folder,
            'exec':   self.exec,
            "clean":  self.clean,
            "args":  self.args,
            "format_args":  self.format_args,
        } )


@dataclass
class DownloaderConfigArg():
    tag: str
    value: Any | None = None
    default_value: Any | None = None
    conditions: List[ Any ] = field( default_factory=list )


@dataclass
class DownloaderConfigFArg(DownloaderConfigArg):
    tag: str | None = None


@dataclass
class DownloaderConfigClean():
    folder: str = ''
    time:   int = 0


@dataclass
class DownloaderContext():
    save_folder:   str | os.PathLike
    exec_folder:   str | os.PathLike
    temp_folder:   str | os.PathLike
    arch_folder:   str | os.PathLike
    file_limit:    int
    downloader:    DownloaderConfigExec
    compression:   Dict[ str, Dict[ str, str | os.PathLike ] ] = field( default_factory=dict )
    proxy:         str = ""
    flaresolverr:  str = ""
    pattern:       str = "{Book.Title}"
    page_delay:    int = 0


    def __export__( self ) -> Dict[ str, Any ]:
        return {
            'save_folder':  self.save_folder,
            'exec_folder':  self.exec_folder,
            'temp_folder':  self.temp_folder,
            'arch_folder':  self.arch_folder,
            'compression':  self.compression,
            'proxy':        self.proxy,
            'flaresolverr': self.flaresolverr,
            'pattern':      self.pattern,
            'page_delay':   self.page_delay,
            'file_limit':   self.file_limit,
        }


    def __repr__( self ) -> str:
        return str( self.__export__() )
