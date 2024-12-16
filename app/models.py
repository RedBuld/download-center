from __future__ import annotations

import json
from typing import Self
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import BigInteger, Boolean, String, Text, UniqueConstraint, Date, DateTime
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped

from app import dto

class Base(AsyncAttrs, DeclarativeBase):
    pass

class SiteStat(Base):
    __tablename__ = 'sites_stats'
    __table_args__ = ( UniqueConstraint("site", "day", name="site_day_index"), )

    id: Mapped[int] =        mapped_column('id', BigInteger, primary_key=True)
    site: Mapped[str] =      mapped_column('site', String(100), nullable=False)
    day: Mapped[datetime] =  mapped_column('day', Date, default=datetime.today)
    success: Mapped[int] =   mapped_column('success', BigInteger, default=1)
    failure: Mapped[int] =   mapped_column('failure', BigInteger, default=1)
    orig_size: Mapped[int] = mapped_column('orig_size', BigInteger, default=0)
    oper_size: Mapped[int] = mapped_column('oper_size', BigInteger, default=0)

class DownloadRequest(Base):
    __tablename__ = "download_requests"

    task_id: Mapped[int] =    mapped_column('task_id', BigInteger, primary_key=True)
    user_id: Mapped[int] =    mapped_column('user_id', BigInteger, default=0)
    bot_id: Mapped[str] =     mapped_column('bot_id', String(10), nullable=True)
    web_id: Mapped[str] =     mapped_column('web_id', String(20), nullable=True)
    chat_id: Mapped[int] =    mapped_column('chat_id', BigInteger, default=0)
    message_id: Mapped[int] = mapped_column('message_id', BigInteger, default=0)
    site: Mapped[str] =       mapped_column('site', String(100), default="")
    url: Mapped[str] =        mapped_column('url', Text, default="")
    start: Mapped[int] =      mapped_column('start_chapter', BigInteger, default=0)
    end: Mapped[int] =        mapped_column('end_chapter', BigInteger, default=0)
    format: Mapped[str] =     mapped_column('format', String(20), default="fb2")
    login: Mapped[str] =      mapped_column('login', Text, default="")
    password: Mapped[str] =   mapped_column('password', Text, default="")
    images: Mapped[bool] =    mapped_column('images', Boolean, default=True)
    cover: Mapped[bool] =     mapped_column('cover', Boolean, default=False)
    hashtags: Mapped[str] =   mapped_column('hashtags', String(5), default="no")
    filename: Mapped[str] =   mapped_column('filename', Text, nullable=True)
    proxy: Mapped[str] =      mapped_column('proxy', Text, default="")

    def __export__(self) -> dict:
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

    def __repr__(self) -> str:
        return str(self.__export__())
    
    @classmethod
    def from_dto( cls, dto: dto.DownloadRequest ) -> Self:
        request = cls()
        
        request.task_id    = dto.task_id
        request.user_id    = dto.user_id
        request.bot_id     = dto.bot_id
        request.web_id     = dto.web_id
        request.chat_id    = dto.chat_id
        request.message_id = dto.message_id
        request.site       = dto.site
        request.url        = dto.url
        request.start      = dto.start
        request.end        = dto.end
        request.format     = dto.format
        request.login      = dto.login
        request.password   = dto.password
        request.images     = dto.images
        request.cover      = dto.cover
        request.hashtags   = dto.hashtags
        request.filename   = dto.filename
        request.proxy      = dto.proxy

        return request
    
    def to_dto( self ) -> dto.DownloadRequest:
        return dto.DownloadRequest.model_validate( self, from_attributes=True )


class DownloadResult(Base):
    __tablename__ = "download_results"

    secure: str =             ""
    task_id: Mapped[int] =    mapped_column('task_id', BigInteger, primary_key=True)
    user_id: Mapped[int] =    mapped_column('user_id', BigInteger, default=0)
    bot_id: Mapped[str] =     mapped_column('bot_id', String(10), nullable=True)
    web_id: Mapped[str] =     mapped_column('web_id', String(20), nullable=True)
    chat_id: Mapped[int] =    mapped_column('chat_id', BigInteger, default=0)
    message_id: Mapped[int] = mapped_column('message_id', BigInteger, default=0)
    status: Mapped[int] =     mapped_column('status', BigInteger, default=1)
    site: Mapped[str] =       mapped_column('site', String(100), default="")
    text: Mapped[str] =       mapped_column('text', Text, default="")
    cover: Mapped[str] =      mapped_column('cover', Text, default="")
    _files: Mapped[str] =     mapped_column('files', Text, default="")
    orig_size: Mapped[int] =  mapped_column('orig_size', BigInteger, default=0)
    oper_size: Mapped[int] =  mapped_column('oper_size', BigInteger, default=0)
    folder: Mapped[str] =     mapped_column('folder', Text, default="")
    proxy: Mapped[str] =      mapped_column('proxy', Text, default="")
    url: Mapped[str] =        mapped_column('url', Text, default="")
    format: Mapped[str] =     mapped_column('format', String(10), default="")
    start: Mapped[int] =      mapped_column('start', BigInteger, default=0)
    end: Mapped[int] =        mapped_column('end', BigInteger, default=0)

    @property
    def files(self):
        return json.loads(self._files)

    @files.setter
    def files(self, value):
        self._files = json.dumps(value)
    
    def _from_dto( self, dto: dto.DownloadResult ) -> Self:
        self.task_id    = dto.task_id
        self.user_id    = dto.user_id
        self.bot_id     = dto.bot_id
        self.web_id     = dto.web_id
        self.chat_id    = dto.chat_id
        self.message_id = dto.message_id
        self.status     = dto.status
        self.site       = dto.site
        self.text       = dto.text
        self.cover      = dto.cover
        self.files      = dto.files
        self.orig_size  = dto.orig_size
        self.oper_size  = dto.oper_size
        self.folder     = dto.folder
        self.proxy      = dto.proxy
        self.url        = dto.url
        self.format     = dto.format
        self.start      = dto.start
        self.end        = dto.end

    @classmethod
    def from_dto( cls, dto: dto.DownloadResult ) -> Self:
        result = cls()
        result._from_dto( dto )

        return result
    
    def to_dto( self ) -> dto.DownloadResult:
        return dto.DownloadResult.model_validate( self, from_attributes=True )


class DownloadHistory(Base):
    __tablename__ = "downloads_history"

    id: Mapped[int] =         mapped_column('id', BigInteger, primary_key=True)
    user_id: Mapped[int] =    mapped_column('user_id', BigInteger, default=0)
    url: Mapped[str] =        mapped_column('url', Text, default="")
    site: Mapped[str] =       mapped_column('site', String(100), default="")
    format: Mapped[str] =     mapped_column('format', String(10), default="")
    orig_size: Mapped[int] =  mapped_column('orig_size', BigInteger, default=0)
    oper_size: Mapped[int] =  mapped_column('oper_size', BigInteger, default=0)
    start: Mapped[int] =      mapped_column('start', BigInteger, default=0)
    end: Mapped[int] =        mapped_column('end', BigInteger, default=0)
    dbg_log: Mapped[str] =    mapped_column('dbg_log', Text, nullable=True)
    dbg_config: Mapped[str] = mapped_column('dbg_config', Text, nullable=True)
    ended: Mapped[datetime] = mapped_column('ended', DateTime)

    @classmethod
    def from_dto( cls, dto: dto.DownloadResult ) -> Self:
        history = cls()
        history.user_id    = dto.user_id
        history.url        = dto.url
        history.site       = dto.site
        history.format     = dto.format
        history.start      = dto.start
        history.end        = dto.end
        history.orig_size  = dto.orig_size
        history.oper_size  = dto.oper_size
        history.dbg_log    = dto.dbg_log
        history.dbg_config = dto.dbg_config
        history.ended      = datetime.now()
        return history