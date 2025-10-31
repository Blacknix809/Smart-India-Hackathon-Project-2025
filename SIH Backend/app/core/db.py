from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
import os

DATABASE_URL = os.getenv("DATABASE_URL")

pool: AsyncConnectionPool | None = None

async def init_pool():
    global pool
    if pool is None:
        pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            open=True,
            kwargs={"row_factory": dict_row}
        )

async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None
