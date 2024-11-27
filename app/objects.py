import os
import redis.asyncio as redis
from app.classes.database import DataBase
from app.classes.interconnect import Interconnect
from app.configs import GC

DB = DataBase()

RD = redis.Redis.from_url( GC.redis_server, protocol=3, decode_responses=True )

IC = Interconnect()