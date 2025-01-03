from __future__ import annotations
import asyncio
import aiohttp
import ujson
import traceback
import logging
from app import dto
from app.configs import GC

logger = logging.getLogger(__name__)

class Interconnect():

    async def Send(
        self,
        data: dto.DownloadResult | dto.DownloadStatus
    ) -> bool:
        
        _type = str( type( data ).__name__ )
        
        if _type == 'DownloadStatus':
            return await self.send_status( data )
        elif _type == 'DownloadResult':
            return await self.send_result( data )
        else:
            return False

    async def send_status(
        self,
        status: dto.DownloadStatus
    ) -> bool:
        if status.web_id:
            return await self.send_web_status( status )
        else:
            return await self.send_bot_status( status )

    async def send_result(
        self,
        data: dto.DownloadResult
    ) -> bool:
        if data.web_id:
            return await self.send_web_result( data )
        else:
            return await self.send_bot_result( data )
    
    #

    async def send_web_status(
        self,
        data: dto.DownloadStatus
    ) -> bool:
        status = False
        return status

    async def send_bot_status(
        self,
        data: dto.DownloadStatus
    ) -> bool:
        status = False

        _attempts = 0
        while _attempts < 5:
            try:
                async with aiohttp.ClientSession( json_serialize=ujson.dumps ) as session:
                    async with session.post( GC.bot_host + 'download/status', json=data.model_dump( mode='json' ), verify_ssl=False ) as response:
                        if response.status == 200:
                            _attempts = 5
                            status = True
                        else:
                            _attempts+=1
                            await asyncio.sleep(1)
            except:
                traceback.print_exc()
                _attempts+=1
                await asyncio.sleep(1)
        
        return status
    
    #

    async def send_web_result(
        self,
        data: dto.DownloadResult
    ) -> bool:
        status = False
        return status

    async def send_bot_result(
        self,
        data: dto.DownloadResult
    ) -> bool:
        status = False

        _attempts = 0
        while _attempts < 5:
            try:
                async with aiohttp.ClientSession( json_serialize=ujson.dumps ) as session:
                    async with session.post( GC.bot_host + 'download/done', json=data.model_dump( mode='json' ), verify_ssl=False ) as response:
                        if response.status == 200:
                            _attempts = 5
                            status = True
                        else:
                            _attempts+=1
                            await asyncio.sleep(1)
            except:
                traceback.print_exc()
                _attempts+=1
                await asyncio.sleep(1)
        return status