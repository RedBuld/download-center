import os
import ujson
import traceback
import logging
import asyncio
import calendar
from typing import Dict, Any
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, delete, func, desc
from sqlalchemy import create_engine
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.exc import *
from sqlalchemy.dialects.mysql import insert
from app import variables
from app import models

logger = logging.getLogger(__name__)

class DataBase(object):
    _engine: Engine = None
    _session: sessionmaker[Session] = None

    __server: str = ""

    def __init__(self):
        config_file = os.path.join( os.getcwd(), 'app', 'configs', 'database.json' )

        config: Dict[str,Any] = {}

        if not os.path.exists(config_file):
            raise FileNotFoundError(config_file)

        with open( config_file, 'r', encoding='utf-8' ) as _config_file:
            _config = _config_file.read()
            config = ujson.loads( _config )

        self.__server = config['server'] if 'server' in config else ""
    
    async def Start(self) -> None:
        if self._engine:
            return

        while True:
            logger.info('DB: starting')
            try:
                if not self._engine:
                    self._engine = create_engine(
                        self.__server,
                        pool_size=5, max_overflow=5, pool_recycle=60, pool_pre_ping=True
                    )
                    self._session = sessionmaker(self._engine, expire_on_commit=False)
                await self._create_db()
                logger.info('DB: started')
                return
            except:
                traceback.print_exc()
                await asyncio.sleep(1)
                continue
    
    async def Stop(self) -> None:
        if self._engine:
            logger.info('DB: finished')
            self._engine.dispose()
            self._engine = None
            self._session = None

    async def _create_db(self) -> None:
        if self._engine:
            logger.info('DB: validate database')
            models.Base.metadata.create_all( bind=self._engine, checkfirst=True )
            logger.info('DB: validated database')
            # logger.info('DB: validate database')
            # async with self._engine.begin() as conn:
            #     await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            #     await conn.commit()
    
    async def UpdateConfig(self) -> None:
        self.__init__()
        if self._engine:
            await self.Stop()
            await self.Start()
        
    
    #

    async def SaveRequest(self, request: dict) -> models.DownloadRequest:
        logger.info('saveRequest')
        logger.info(request)
        
        session = self._session()
        try:
            result = models.DownloadRequest(**request)
            session.add(result)
            session.commit()
            session.close()
            return result
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.SaveRequest(request)
        except Exception as e:
            raise e
        finally:
            session.close()
    
    async def GetRequest(self, task_id: int) -> models.DownloadRequest | None:
        session = self._session()
        try:
            query = session.execute(
                select(models.DownloadRequest).where(models.DownloadRequest.task_id==task_id)
            )
            result = query.scalar_one_or_none()
            session.close()
            if not result:
                return None
            return result
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.GetRequest(task_id)
        except Exception as e:
            raise e
        finally:
            session.close()
    
    async def GetAllRequests(self) -> list[models.DownloadRequest]:
        session = self._session()
        try:
            query = session.execute(
                select(models.DownloadRequest)
            )
            result = query.scalars().all()
            session.close()
            return result
        except OperationalError as e:
            traceback.print_exception()
            await asyncio.sleep(1)
            return await self.GetAllRequests()
        except Exception as e:
            raise e
        finally:
            session.close()
    
    async def DeleteRequest(self, task_id: int) -> None:
        session = self._session()
        try:
            session.execute(
                delete(models.DownloadRequest).where(models.DownloadRequest.task_id==task_id)
            )
            session.commit()
            session.close()
        except OperationalError as e:
            traceback.print_exception()
            await asyncio.sleep(1)
            return await self.DeleteRequest(task_id)
        except Exception as e:
            raise e
        finally:
            session.close()

    #

    async def SaveResult(self, _result: dict) -> models.DownloadResult:
        session = self._session()
        try:
            query = session.execute(
                select(models.DownloadResult).where(models.DownloadResult.task_id==_result['task_id'])
            )
            result = query.scalar_one_or_none()
            if not result:
                result = models.DownloadResult(**_result)
            session.add(result)
            session.commit()
            return result
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.SaveResult(_result)
        except Exception as e:
            raise e
        finally:
            session.close()
    
    async def GetResult(self, task_id: int) -> models.DownloadResult | None:
        session = self._session()
        try:
            query = session.execute(
                select(models.DownloadResult).where(models.DownloadResult.task_id==task_id)
            )
            result = query.scalar_one_or_none()
            session.close()
            if not result:
                return None
            return result
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.GetResult(task_id)
        except Exception as e:
            raise e
        finally:
            session.close()
    
    async def GetAllResults(self) -> list[models.DownloadResult]:
        session = self._session()
        try:
            query = session.execute(
                select(models.DownloadResult)
            )
            result = query.scalars().all()
            session.close()
            return result
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.GetAllResults()
        except Exception as e:
            raise e
        finally:
            session.close()
    
    async def DeleteResult(self, task_id: int) -> None:
        session = self._session()
        try:
            session.execute(
                delete(models.DownloadResult).where(models.DownloadResult.task_id==task_id)
            )
            session.commit()
            session.close()
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.DeleteResult(task_id)
        except Exception as e:
            raise e
        finally:
            session.close()

    #

    async def AddHistory(self, result: dict) -> models.DownloadHistory:
        session = self._session()
        try:
            history = models.DownloadHistory.from_result(**result)
            session.add(history)
            session.commit()
            return history
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.AddHistory(result)
        except Exception as e:
            raise e
        finally:
            session.close()
    
    #

    async def UpdateSiteStat(self, result: dict) -> None:

        if result['status'] == variables.DownloaderStep.CANCELLED:
            return

        success = 1 if result['status'] == variables.DownloaderStep.DONE else 0
        failure = 1 if result['status'] == variables.DownloaderStep.ERROR else 0

        session = self._session()
        try:
            ss = {
                'site': result['site'],
                'day': datetime.today(),
                'success': success,
                'failure': failure,
                'orig_size': result['orig_size'],
                'oper_size': result['oper_size'],
            }
            session.execute(
                insert(models.SiteStat)\
                .values(**ss)\
                .on_duplicate_key_update(
                    success=models.SiteStat.success + success,
                    failure=models.SiteStat.failure + failure,
                    orig_size=models.SiteStat.orig_size + result['orig_size'],
                    oper_size=models.SiteStat.oper_size + result['oper_size'],
                )
            )
            session.commit()
            session.close()
        except OperationalError as e:
            await asyncio.sleep(1)
            traceback.print_exc()
            return await self.UpdateSiteStat(result)
        except Exception as e:
            raise e
        finally:
            session.close()
    
    #

    async def GetStats(self):

        session = self._session()

        current_date = datetime.now()

        current_day = current_date
        previous_day = current_date - timedelta(days=1)

        current_month_start = current_date.replace(day=1)
        current_month_end = current_month_start - timedelta(days=1) + relativedelta(months=1)
        
        # previous_month_start = current_date.replace(day=1) + relativedelta(months=1)
        # previous_month_end = previous_month_start.replace() - timedelta(days=1) + relativedelta(months=1)

        current_year_start = current_date.replace(month=1,day=1)
        current_year_end = current_year_start.replace(year=current_year_start.year+1) - timedelta(days=1)

        previous_year_start = current_date.replace(year=current_date.year-1,month=1,day=1)
        previous_year_end = previous_year_start.replace(year=previous_year_start.year+1) - timedelta(days=1)

        #strftime("%Y-%m-%d")

        current_day_stats_query = session.execute(
            select(
                models.SiteStat.site,
                func.sum(models.SiteStat.success),
                func.sum(models.SiteStat.failure),
                func.sum(models.SiteStat.orig_size).label("orig_size"),
                func.sum(models.SiteStat.oper_size).label("oper_size"),
            )
            .where(
                models.SiteStat.day == current_day.date()
            )
            .group_by(models.SiteStat.site)
            .order_by(desc("orig_size"))
        )
        current_day_stats = current_day_stats_query.all()

        previous_day_stats_query = session.execute(
            select(
                models.SiteStat.site,
                func.sum(models.SiteStat.success),
                func.sum(models.SiteStat.failure),
                func.sum(models.SiteStat.orig_size).label("orig_size"),
                func.sum(models.SiteStat.oper_size).label("oper_size"),
            )
            .where(
                models.SiteStat.day == previous_day.date()
            )
            .group_by(models.SiteStat.site)
            .order_by(desc("orig_size"))
        )
        previous_day_stats = previous_day_stats_query.all()

        ###

        current_month_stats_query = session.execute(
            select(
                models.SiteStat.site,
                func.sum(models.SiteStat.success),
                func.sum(models.SiteStat.failure),
                func.sum(models.SiteStat.orig_size).label("orig_size"),
                func.sum(models.SiteStat.oper_size).label("oper_size"),
            )
            .where(
                models.SiteStat.day.between(current_month_start.date(),current_month_end.date())
            )
            .group_by(models.SiteStat.site)
            .order_by(desc("orig_size"))
        )
        current_month_stats = current_month_stats_query.all()

        # previous_month_stats_query = session.execute(
        #     select(
        #         models.SiteStat.site,
        #         func.sum(models.SiteStat.success),
        #         func.sum(models.SiteStat.failure),
        #         func.sum(models.SiteStat.orig_size).label("orig_size"),
        #         func.sum(models.SiteStat.oper_size).label("oper_size"),
        #     )
        #     .where(
        #         models.SiteStat.day.between(previous_month_start.date(),previous_month_end.date())
        #     )
        #     .group_by(models.SiteStat.site)
        #     .order_by(desc("orig_size"))
        # )
        # previous_month_stats = previous_month_stats_query.all()

        ###

        current_year_stats_query = session.execute(
            select(
                models.SiteStat.site,
                func.sum(models.SiteStat.success),
                func.sum(models.SiteStat.failure),
                func.sum(models.SiteStat.orig_size).label("orig_size"),
                func.sum(models.SiteStat.oper_size).label("oper_size"),
            )
            .where(
                models.SiteStat.day.between(current_year_start.date(),current_year_end.date())
            )
            .group_by(models.SiteStat.site)
            .order_by(desc("orig_size"))
        )
        current_year_stats = current_year_stats_query.all()

        previous_year_stats_query = session.execute(
            select(
                models.SiteStat.site,
                func.sum(models.SiteStat.success),
                func.sum(models.SiteStat.failure),
                func.sum(models.SiteStat.orig_size).label("orig_size"),
                func.sum(models.SiteStat.oper_size).label("oper_size"),
            )
            .where(
                models.SiteStat.day.between(previous_year_start.date(),previous_year_end.date())
            )
            .group_by(models.SiteStat.site)
            .order_by(desc("orig_size"))
        )
        previous_year_stats = previous_year_stats_query.all()

        total_stats_query = session.execute(
            select(
                models.SiteStat.site,
                func.sum(models.SiteStat.success),
                func.sum(models.SiteStat.failure),
                func.sum(models.SiteStat.orig_size).label("orig_size"),
                func.sum(models.SiteStat.oper_size).label("oper_size"),
            )
            .group_by(models.SiteStat.site)
            .order_by(desc("orig_size"))
        )
        total_stats = total_stats_query.all()

        fields = ['site','success','failure','orig_size','oper_size']

        session.close()
        return {
            'current_day': {
                'elements': [ dict( zip(fields, x) ) for x in current_day_stats ],
            },
            'previous_day': {
                'elements': [dict( zip(fields, x) ) for x in previous_day_stats ],
            },
            'current_month': {
                'elements': [ dict( zip(fields, x) ) for x in current_month_stats ],
            },
            # 'previous_month': {
            #     'elements': [ dict(zip(fields, x) ) for x in previous_month_stats ],
            # },
            'current_year': {
                'elements': [ dict( zip(fields, x) ) for x in current_year_stats ],
            },
            'previous_year': {
                'elements': [ dict( zip(fields, x) ) for x in previous_year_stats ],
            },
            'total': {
                'elements': [ dict( zip(fields, x) ) for x in total_stats ],
            },
        }