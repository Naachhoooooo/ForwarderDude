import aiosqlite
import asyncio
from app.config import Config
from app.logger import error_logger

class Database:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_path = Config.DB_PATH
            cls._instance.conn = None
        return cls._instance

    def __init__(self):
        pass
    
    async def connect(self):
        if self.conn:
            return
            
        async with self._lock:
            if self.conn:
                return
                
            try:
                self.conn = await aiosqlite.connect(self.db_path)
                self.conn.row_factory = aiosqlite.Row
                await self._configure_pragmas(self.conn)
            except Exception as e:
                error_logger.critical(f"Failed to connect to database: {e}")
                raise

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def execute(self, query, params=()):
        if not self.conn:
            await self.connect()
            
        try:
            async with self.conn.execute(query, params) as cursor:
                await self.conn.commit()
                return cursor
        except Exception as e:
            error_logger.error(f"Database Error: {e} | Query: {query}")
            raise

    async def fetch_one(self, query, params=()):
        if not self.conn:
            await self.connect()

        try:
            async with self.conn.execute(query, params) as cursor:
                return await cursor.fetchone()
        except Exception as e:
            error_logger.error(f"Database Fetch Error: {e} | Query: {query}")
            raise

    async def fetch_all(self, query, params=()):
        if not self.conn:
            await self.connect()

        try:
            async with self.conn.execute(query, params) as cursor:
                return await cursor.fetchall()
        except Exception as e:
            error_logger.error(f"Database Fetch All Error: {e} | Query: {query}")
            raise
    
    async def _configure_pragmas(self, conn):
        try:
            await conn.execute('PRAGMA journal_mode=WAL;')
            await conn.execute('PRAGMA synchronous=NORMAL;')
            await conn.execute('PRAGMA foreign_keys=ON;')
        except Exception:
            pass
