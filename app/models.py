import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy import BigInteger, Boolean, String, Text, UniqueConstraint, Date, DateTime
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship

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

    @property
    def dict(self) -> dict:
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
        return str(self.dict)

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


class DownloadHistory(Base):
    __tablename__ = "downloads_history"

    id: Mapped[int] =         mapped_column('id', BigInteger, primary_key=True)
    user_id: Mapped[int] =    mapped_column('user_id', BigInteger, default=0)
    url: Mapped[str] =        mapped_column('url', Text, default="")
    site: Mapped[str] =       mapped_column('site', String(100), default="")
    format: Mapped[str] =     mapped_column('format', String(10), default="")
    ended: Mapped[datetime] = mapped_column('ended', DateTime)
    orig_size: Mapped[int] =  mapped_column('orig_size', BigInteger, default=0)
    oper_size: Mapped[int] =  mapped_column('oper_size', BigInteger, default=0)
    start: Mapped[int] =      mapped_column('start', BigInteger, default=0)
    end: Mapped[int] =        mapped_column('end', BigInteger, default=0)
    dbg_log: Mapped[str] =    mapped_column('dbg_log', Text, nullable=True)
    dbg_config: Mapped[str] = mapped_column('dbg_config', Text, nullable=True)

    @classmethod
    def from_result( cls, **data ):
        res = DownloadHistory()
        res.user_id = data['user_id'] if 'user_id' in data else None
        res.url = data['url'] if 'url' in data else None
        res.site = data['site'] if 'site' in data else None
        res.format = data['format'] if 'format' in data else None
        res.start = data['start'] if 'start' in data else None
        res.end = data['end'] if 'end' in data else None
        res.ended = datetime.now()
        res.orig_size = data['orig_size'] if 'orig_size' in data else None
        res.oper_size = data['oper_size'] if 'oper_size' in data else None
        res.dbg_log = data['dbg_log'] if 'dbg_log' in data else None
        res.dbg_config = data['dbg_config'] if 'dbg_config' in data else None
        return res