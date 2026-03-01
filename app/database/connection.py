import aiosqlite
import asyncio
from app.config import Config
from app.logger import error_logger

class MockCursor:
    def __init__(self, lastrowid, rowcount):
        self.lastrowid = lastrowid
        self.rowcount = rowcount

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_path = Config.DB_PATH
        return cls._instance

    def __init__(self):
        pass
    
    async def connect(self):
        pass

    async def close(self):
        pass

    async def _configure_pragmas(self, conn):
        try:
            await conn.execute('PRAGMA journal_mode=WAL;')
            await conn.execute('PRAGMA synchronous=NORMAL;')
            await conn.execute('PRAGMA foreign_keys=ON;')
        except Exception:
            pass

    async def _get_conn(self):
        try:
            conn = await aiosqlite.connect(self.db_path)
            conn.row_factory = aiosqlite.Row
            await self._configure_pragmas(conn)
            return conn
        except Exception as e:
            error_logger.critical(f"Failed to connect to database: {e}")
            raise

    async def execute(self, query, params=()):
        conn = await self._get_conn()
        try:
            async with conn.execute(query, params) as cursor:
                await conn.commit()
                res = MockCursor(cursor.lastrowid, cursor.rowcount)
                return res
        except Exception as e:
            error_logger.error(f"Database Error: {e} | Query: {query}")
            raise
        finally:
            await conn.close()

    async def fetch_one(self, query, params=()):
        conn = await self._get_conn()
        try:
            async with conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            error_logger.error(f"Database Fetch Error: {e} | Query: {query}")
            raise
        finally:
            await conn.close()

    async def fetch_all(self, query, params=()):
        conn = await self._get_conn()
        try:
            async with conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            error_logger.error(f"Database Fetch All Error: {e} | Query: {query}")
            raise
        finally:
            await conn.close()
