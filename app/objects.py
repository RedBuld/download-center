import os
import redis.asyncio as redis
from app.classes.database import DataBase
from app.classes.interconnect import Interconnect

DB = DataBase()

_redis_server = os.environ.get("REDIS_SERVER")
if _redis_server:
    RD = redis.Redis.from_url( _redis_server, protocol=3, decode_responses=True )
else:
    RD = None

IC = Interconnect()