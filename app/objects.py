import redis.asyncio as redis
from app.classes.database import DataBase
from app.classes.interconnect import Interconnect

DB = DataBase()

RD = redis.Redis( host='127.0.0.1', port=6379, db=1, protocol=3, decode_responses=True )

IC = Interconnect()