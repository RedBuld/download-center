from __future__ import annotations

import os
from pydantic import BaseModel, Field, computed_field
from typing import Any, List, Dict

class SiteCheckRequest(BaseModel):
    site: str

class DownloadRequest(BaseModel):
    task_id:    int | None = None
    user_id:    int
    bot_id:     str | None = None
    web_id:     str | None = None
    chat_id:    int | None = None
    message_id: int | None = None
    site:       str
    url:        str
    start:      int | None = 0
    end:        int | None = 0
    format:     str | None = "fb2"
    login:      str | None = ""
    password:   str | None = ""
    images:     bool | None = False
    cover:      bool | None = False
    proxy:      str | None = ""
    hashtags:   str | None = ""
    filename:   str | None = None

    class Config:
        from_attributes = True

    def __export__(self) -> Dict:
        return {
            'task_id':    self.task_id,
            'user_id':    self.user_id,
            'bot_id':     self.bot_id,
            'web_id':     self.web_id,
            'chat_id':    self.chat_id,
            'message_id': self.message_id,
            'site':       self.site,
            'url':        self.url,
            'start':      self.start,
            'end':        self.end,
            'format':     self.format,
            'login':      self.login,
            'password':   self.password,
            'images':     self.images,
            'cover':      self.cover,
            'hashtags':   self.hashtags,
            'proxy':      self.proxy,
        }

class DownloadCancelRequest(BaseModel):
    task_id:    int

class DownloadClearRequest(BaseModel):
    task_id:    int

#

class SiteCheckResponse(BaseModel):
    allowed:    bool = False
    parameters: List[ str ] = []
    formats:    Dict[ str, List[ str ] ] = {}

class SiteListResponse(BaseModel):
    sites: List[ str ]

class DownloadResponse(BaseModel):
    status:  bool = False
    message: str = ""
    task_id: int | None = None

class DownloadCancelResponse(BaseModel):
    user_id:    int
    bot_id:     str | None = None
    web_id:     str | None = None
    chat_id:    int
    message_id: int

class ExportStatsResponse(BaseModel):
    current_day:    ExportStatsResponseGroup
    previous_day:   ExportStatsResponseGroup
    current_month:  ExportStatsResponseGroup
    # previous_month: ExportStatsResponseGroup
    current_year:   ExportStatsResponseGroup
    previous_year:  ExportStatsResponseGroup
    total:          ExportStatsResponseGroup

    class Config:
        from_attributes = True

class ExportQueueResponse(BaseModel):
    stats:   Dict[ str, Dict[ str, Any ] ] = {}
    waiting: List[ ExportQueueWaitingGroup ] = []
    running: List[ ExportQueueRunningGroup ] = []

    class Config:
        from_attributes = True

#

class ExportStatsResponseGroup(BaseModel):
    elements: List[ ExportStatsResponseElement ] = []

    @computed_field
    @property
    def total(self) -> ExportStatsResponseElement:

        success:   int = 0
        failure:   int = 0
        orig_size: int = 0
        oper_size: int = 0

        for element in self.elements:
            success   += element.success
            failure   += element.failure
            orig_size += element.orig_size
            oper_size += element.oper_size

        return ExportStatsResponseElement(
            site      = 'Всего',
            success   = success,
            failure   = failure,
            orig_size = orig_size,
            oper_size = oper_size,
        )

    class Config:
        from_attributes = True

class ExportStatsResponseElement(BaseModel):
    site:      str = ""
    success:   int = 0
    failure:   int = 0
    orig_size: int = 0
    oper_size: int = 0

    class Config:
        from_attributes = True

class ExportQueueWaitingGroup(BaseModel):
    name:  str
    tasks: List[ ExportQueueWaitingTask ] = []

    class Config:
        from_attributes = True

class ExportQueueRunningGroup(BaseModel):
    name:  str
    tasks: List[ ExportQueueRunningTask ] = []

    class Config:
        from_attributes = True

#

class ExportQueueWaitingTask(BaseModel):
    task_id: int
    request: DownloadRequest

    class Config:
        from_attributes = True

class ExportQueueRunningTask(BaseModel):
    task_id: int
    request: DownloadRequest
    status:  str

    class Config:
        from_attributes = True

#

class DownloadResult(BaseModel):
    task_id:    int
    user_id:    int
    bot_id:     str | None = None
    web_id:     str | None = None
    chat_id:    int | None = None
    message_id: int | None = None
    site:       str = ''
    proxy:      str | None = ""
    url:        str | None = ''
    format:     str | None = ''
    start:      int | None = 0
    end:        int | None = 0
    status:     int
    text:       str = ''
    cover:      str | os.PathLike
    files:      List[ str | os.PathLike ]
    orig_size:  int = 0
    oper_size:  int = 0
    dbg_log:    str | None = None
    dbg_config: str | None = None

    class Config:
        from_attributes = True

class DownloadStatus(BaseModel):
    task_id:    int
    user_id:    int
    bot_id:     str | None = None
    web_id:     str | None = None
    chat_id:    int | None = None
    message_id: int | None = None
    text:       str = ''
    status:     int