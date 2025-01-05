import traceback
import asyncio
import logging
import aiohttp
import ujson
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from app import dto, variables
from app.configs import GC, DC, QC
from app.objects import DB, RD

logging.basicConfig(
    format='%(levelname)s: %(name)s[%(process)d] - %(asctime)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger( __name__ )

async def request_validation_error_exception_handler( request: Request, exc: RequestValidationError ):
    logger.info( exc )
    validation_errors = exc.errors()
    return JSONResponse(
        status_code = 500,
        content =     { "detail": [ str( err ) for err in validation_errors ] }
    )

async def response_validation_error_exception_handler( request: Request, exc: ResponseValidationError ):
    logger.info( exc )
    validation_errors = exc.errors()
    return JSONResponse(
        status_code = 500,
        content =     { "detail": [ str( err ) for err in validation_errors ] }
    )

async def base_error_exception_handler( request: Request, exc: Exception ):
    logger.info( exc )
    return JSONResponse(
        status_code = 500,
        content =     { "detail": str( exc ) }
    )

####

from app.classes.download_queue import DownloadsQueue

DQ = DownloadsQueue()

@asynccontextmanager
async def lifespan( app: FastAPI ):
    logging.getLogger("fastapi.access").handlers.clear()
    logging.getLogger("fastapi.access").propagate = False
    logger.info('starting app')
    await read_config()
    await DB.Start()
    await DQ.Start()
    yield
    logger.info('stopping app')
    await DQ.Save()
    await DQ.Stop()
    await DQ.Close()
    await DB.Stop()
    if RD is not None:
        await RD.close()

app = FastAPI(
    docs_url=None,
    openapi_url=None,
    exception_handlers={
        RequestValidationError: request_validation_error_exception_handler,
        ResponseValidationError: response_validation_error_exception_handler,
        Exception: base_error_exception_handler
    },
    lifespan=lifespan
)


#UPDATE CONFIG
async def read_config():
    await GC.UpdateConfig()
    await DC.UpdateConfig()
    await QC.UpdateConfig()
    #
    await DB.UpdateConfig()
    await DQ.UpdateConfig()

#

@app.get('/update_config')
async def update_config():
    await read_config()

#

@app.get('/export/queue')
async def export_queue():
    data = await DQ.ExportQueue()
    resp = dto.ExportQueueResponse(**data)
    return resp

@app.get('/export/stats')
async def export_stats():
    data = await DB.GetStats()
    resp = dto.ExportStatsResponse(**data)
    return resp

#

@app.post('/sites/check')
async def sites_check( request: dto.SiteCheckRequest ):
    response = await DQ.CheckSite( request.site )
    return response

@app.post('/sites/auths')
async def sites_auths():
    response = await DQ.GetSitesWithAuth()
    return response

@app.post('/sites/active')
async def sites_active():
    response = await DQ.GetSitesActive()
    return response

@app.post('/sites/active_grouped')
async def sites_active_grouped():
    response = await DQ.GetSitesActiveByGroups()
    return response

#

@app.post('/download/new')
async def download_new( request: dto.DownloadRequest ):

    try:
        resp = await asyncio.wait_for( DQ.AddTask( request ), 10 )

        return JSONResponse(
            status_code = 200 if resp.status else 500,
            content =     resp.message
        )
    except variables.QueueCheckException as e:
        return JSONResponse(
            status_code = 500,
            content =     str(e)
        )
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

@app.post('/download/clear')
async def download_clear( request: dto.DownloadClearRequest ):

    try:
        await DQ.ClearFolder( request )
        return JSONResponse(
            status_code = 200,
            content =     None
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

@app.post('/download/cancel')
async def download_cancel( request: dto.DownloadCancelRequest ):
    try:
        resp = await asyncio.wait_for( DQ.CancelTask( request ), 10 )
        return resp
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )


@app.post('/download/get_log')
async def download_cancel( request: dto.DownloadLogRequest ):
    try:
        resp = await asyncio.wait_for( DQ.GetLog( request ), 10 )
        return resp
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

#

@app.post('/queue/stop')
async def queue_stop():
    try:
        await DQ.Stop()
        return JSONResponse(
            status_code = 200,
            content =     ""
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

@app.post('/queue/stop/tasks')
async def queue_stop_tasks():
    try:
        await DQ.StopTasks()
        return JSONResponse(
            status_code = 200,
            content =     ""
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

@app.post('/queue/stop/results')
async def queue_stop_results():
    try:
        await DQ.StopResults()
        return JSONResponse(
            status_code = 200,
            content =     ""
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

#


@app.post('/queue/start')
async def queue_start():
    try:
        await DQ.Start()
        return JSONResponse(
            status_code = 200,
            content =     ""
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

@app.post('/queue/start/tasks')
async def queue_start_tasks():
    try:
        await DQ.StartTasks()
        return JSONResponse(
            status_code = 200,
            content =     ""
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )

@app.post('/queue/start/results')
async def queue_start_results():
    try:
        await DQ.StartResults()
        return JSONResponse(
            status_code = 200,
            content =     ""
        )
    except Exception as e:
        return JSONResponse(
            status_code = 500,
            content =     "Произошла ошибка: "+str(e)
        )