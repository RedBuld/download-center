from __future__ import annotations
import os
import ujson
import traceback
from enum import StrEnum
from dataclasses import dataclass, field
from dacite import from_dict, Config
from typing import TypeVar
from typing import List, Dict, Any

MAX_WAIT = 'max_waiting'

MAX_ONETIME = 'max_one_time'

NONE_USER = 'noneuser'

class _DELAY:
    noneuser = 'delay'
    hasuser = 'delay_per_user'

    def __getattribute__( self, attr ):
        print( '__getattribute__', attr )
        if attr == NONE_USER:
            return object.__getattribute__(self, 'noneuser')
        else:
            return object.__getattribute__(self, 'hasuser')

class _WAIT:
    noneuser = 'waiting'
    hasuser = 'waiting_per_user'

    def __getattribute__( self, attr ):
        print( '__getattribute__', attr )
        if attr == NONE_USER:
            return object.__getattribute__(self, 'noneuser')
        else:
            return object.__getattribute__(self, 'hasuser')

class _ONETIME:
    noneuser = 'one_time'
    hasuser = 'one_time_per_user'

    def __getattribute__( self, attr ):
        print( '__getattribute__', attr )
        if attr == NONE_USER:
            return object.__getattribute__(self, 'noneuser')
        else:
            return object.__getattribute__(self, 'hasuser')

DELAY = _DELAY()
WAIT = _WAIT()
ONETIME = _ONETIME()


class QueueConfig():
    formats_params: Dict[ str, List[ str ] ]
    proxies:        QueueConfigProxies
    flaresolverrs:  QueueConfigFlaresolvers
    groups:         Dict[ str, QueueConfigGroup ]
    sites:          Dict[ str, QueueConfigSite ]
    inited:         bool = False

    def __init__(self) -> None:
        self.formats_params = None
        self.proxies        = None
        self.flaresolverrs  = None
        self.groups         = None
        self.sites          = None
        self.inited         = False

    def __repr__(self) -> str:
        return '<QueueConfig: ' + str( {
            'formats_params': self.formats_params,
            'groups':         self.groups,
            'sites':          self.sites,
            'proxies':        self.proxies,
            'flaresolverrs':  self.flaresolverrs,
         } ) + '>'

    async def UpdateConfig( self ) -> None:
        config_path = []

        cwd = os.getcwd()

        config_path.append( cwd )

        if not cwd.endswith( 'app/' ) and not cwd.endswith( 'app' ):
            config_path.append( 'app' )

        config_file = os.path.join( *config_path, 'configs', 'queue.json' )

        config: Dict[ str, Any ] = {}

        try:
            if not os.path.exists( config_file ):
                raise FileNotFoundError( config_file )

            with open( config_file, 'r', encoding='utf-8' ) as _config_file:
                _config = _config_file.read()
                config = ujson.loads( _config )
        except Exception as e:
            if not self.inited:
                raise e
            traceback.print_exc()

        formats_params = {}
        _formats_params = {}
        if 'formats_params' in config:
            _formats_params = config[ 'formats_params' ]
        for format, format_params in _formats_params.items():
            formats_params[format] = format_params

        groups = {}
        _groups = {}
        if 'groups' in config:
            _groups = config['groups']
        for group_name, group_data in _groups.items():
            groups[ group_name ] = from_dict( data_class=QueueConfigGroup, data=group_data, config=Config( check_types=False ) ) 

        sites = {}
        _sites = {}
        if 'sites' in config:
            _sites = config['sites']
        for site_name, site_data in _sites.items():
            sites[ site_name ] = from_dict( data_class=QueueConfigSite, data=site_data, config=Config( check_types=False ) ) 

        _proxies = []
        if 'proxies' in config:
            _proxies = config['proxies']
        proxies = from_dict( data_class=QueueConfigProxies, data={ 'instances':_proxies }, config=Config( check_types=False ) )
        if self.proxies:
            proxies.last_by_site = self.proxies.last_by_site

        _flaresolverrs = {}
        if 'flaresolverrs' in config:
            _flaresolverrs = config['flaresolverrs']
        flaresolverrs = from_dict( data_class=QueueConfigFlaresolvers, data={ 'instances':_flaresolverrs }, config=Config( check_types=False ) )

        self.formats_params = formats_params
        self.groups = groups
        self.sites = sites
        self.proxies = proxies
        self.flaresolverrs = flaresolverrs


@dataclass
class QueueConfigGroup():
    formats:           List[ str ] = field( default_factory=list )
    downloader:        str = "elib2ebook"
    pattern:           str = "{Book.Title}"
    one_time:          int = 0
    one_time_per_user: int = 0
    delay:             int = 0
    delay_per_user:    int = 0
    waiting:           int = 0
    waiting_per_user:  int = 0
    max_one_time:      int = 0
    max_waiting:       int = 0
    page_delay:        int = 0

    def __repr__(self) -> str:
        return str( {
            'formats':           self.formats,
            'downloader':        self.downloader,
            'pattern':           self.pattern,
            'one_time':          self.one_time,
            'one_time_per_user': self.one_time_per_user,
            'delay':             self.delay,
            'delay_per_user':    self.delay_per_user,
            'waiting':           self.waiting,
            'waiting_per_user':  self.waiting_per_user,
            'max_one_time':      self.max_one_time,
            'max_waiting':       self.max_waiting,
            'page_delay':        self.page_delay,
        } )

@dataclass
class QueueConfigSite():
    parameters:        List[ str ] = field( default_factory=list )
    formats:           List[ str ] = field( default_factory=list )
    allowed_groups:    List[ str ] = field( default_factory=list )
    downloader:        str = "elib2ebook"
    pattern:           str = ""
    active:            bool = True
    force_proxy:       bool = False
    use_flare:         bool = False
    one_time:          int = 0
    one_time_per_user: int = 0
    delay:             int = 0
    delay_per_user:    int = 0
    waiting:           int = 0
    waiting_per_user:  int = 0
    max_one_time:      int = 0
    max_waiting:       int = 0
    page_delay:        int = 0

    def __repr__(self) -> str:
        return str( {
            'parameters':        self.parameters,
            'formats':           self.formats,
            'allowed_groups':    self.allowed_groups,
            'downloader':        self.downloader,
            'pattern':           self.pattern,
            'active':            self.active,
            'force_proxy':       self.force_proxy,
            'use_flare':         self.use_flare,
            'one_time':          self.one_time,
            'one_time_per_user': self.one_time_per_user,
            'delay':             self.delay,
            'delay_per_user':    self.delay_per_user,
            'waiting':           self.waiting,
            'waiting_per_user':  self.waiting_per_user,
            'max_one_time':      self.max_one_time,
            'max_waiting':       self.max_waiting,
            'page_delay':        self.page_delay,
        } )

@dataclass(init=False)
class QueueConfigProxies():
    instances: List[ str ]         = field( default_factory=list )
    last_by_site: Dict[ str, int ] = field( default_factory=dict )

    def __init__(
        self,
        instances: List[ str ],
        last_by_site: Dict[ str, int ] = {}
    ) -> None:
        self.instances    = instances
        self.last_by_site = last_by_site
    
    def Has( self ) -> bool:
        return len( self.instances ) != 0

    async def GetInstance(
        self,
        site: str
    ) -> str:
        index = 0

        if len( self.instances ) == 0:
            return ''
        
        if site in self.last_by_site:
            index = self.last_by_site[ site ]
            index += 1
            if index > len( self.instances ) - 1:
                index = 0

        self.last_by_site[ site ] = index
        return self.instances[ index ]

@dataclass(init=False)
class QueueConfigFlaresolvers():
    instances: Dict[ str, str ] = field( default_factory=list )

    def __init__(
        self,
        instances: Dict[ str, str ]
    ) -> None:
        self.instances = instances
    
    def Has( self ) -> bool:
        return len( self.instances.keys() ) != 0

    async def GetInstance(
        self,
        proxy: str
    ) -> str:        
        if proxy in self.instances:
            return self.instances[ proxy ]

        return ''