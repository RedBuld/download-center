from __future__ import annotations

import os
from pydantic import BaseModel, Field, computed_field
from app import variables, models
from typing import Callable, Optional, Type, Any, List, Dict

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
    hashtags:   str = "no"

    class Config:
        from_attributes = True

class DownloadCancelRequest(BaseModel):
    task_id:    int

class DownloadClearRequest(BaseModel):
    task_id:    int
    folder:     str

#

class SiteCheckResponse(BaseModel):
    allowed: bool
    parameters: List[ str ]
    formats: Dict[ str, List[ str ] ]

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
    current_day: ExportStatsResponseGroup
    previous_day: ExportStatsResponseGroup
    current_month: ExportStatsResponseGroup
    # previous_month: ExportStatsResponseGroup
    current_year: ExportStatsResponseGroup
    previous_year: ExportStatsResponseGroup

    @computed_field
    @property
    def total(self) -> Dict[ str, int ]:

        success: int = 0
        failure: int = 0
        orig_size: int = 0
        oper_size: int = 0

        success += self.current_day.total.success
        failure += self.current_day.total.failure
        orig_size += self.current_day.total.orig_size
        oper_size += self.current_day.total.oper_size

        success += self.previous_day.total.success
        failure += self.previous_day.total.failure
        orig_size += self.previous_day.total.orig_size
        oper_size += self.previous_day.total.oper_size

        success += self.current_month.total.success
        failure += self.current_month.total.failure
        orig_size += self.current_month.total.orig_size
        oper_size += self.current_month.total.oper_size

        success += self.current_year.total.success
        failure += self.current_year.total.failure
        orig_size += self.current_year.total.orig_size
        oper_size += self.current_year.total.oper_size

        success += self.previous_year.total.success
        failure += self.previous_year.total.failure
        orig_size += self.previous_year.total.orig_size
        oper_size += self.previous_year.total.oper_size

        return {
            'success': success,
            'failure': failure,
            'orig_size': orig_size,
            'oper_size': oper_size,
        }

    class Config:
        from_attributes = True

class ExportQueueResponse(BaseModel):
    stats: Dict[ str, Dict[ str, Any ] ] = {}
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

        success: int = 0
        failure: int = 0
        orig_size: int = 0
        oper_size: int = 0

        for element in self.elements:
            success += element.success
            failure += element.failure
            orig_size += element.orig_size
            oper_size += element.oper_size

        return ExportStatsResponseElement(
            site = 'Всего',
            success = success,
            failure = failure,
            orig_size = orig_size,
            oper_size = oper_size,
        )

    class Config:
        from_attributes = True

class ExportStatsResponseElement(BaseModel):
    site: str = ""
    success: int = 0
    failure: int = 0
    orig_size: int = 0
    oper_size: int = 0

    class Config:
        from_attributes = True

class ExportQueueWaitingGroup(BaseModel):
    name: str
    tasks: List[ ExportQueueWaitingTask ] = []

    class Config:
        from_attributes = True

class ExportQueueRunningGroup(BaseModel):
    name: str
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
    last_status: str
    request: DownloadRequest

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
    status:     int
    site:       str
    text:       str
    cover:      str | os.PathLike
    files:      List[ str | os.PathLike ]
    orig_size:  int
    oper_size:  int
    folder:     str
    proxy:      str | None = ""
    url:        str | None = ''

    class Config:
        from_attributes = True

class DownloadStatus(BaseModel):
    task_id:    int
    user_id:    int
    bot_id:     str | None = None
    web_id:     str | None = None
    chat_id:    int | None = None
    message_id: int | None = None
    text:       str
    status:     int