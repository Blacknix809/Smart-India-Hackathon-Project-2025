from fastapi import APIRouter
from app.core.db import pool

router = APIRouter()

@router.get("/healthz")
async def healthz():
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("select 1 as ok;")
            row = await cur.fetchone()
            return {"db": row["ok"], "status": "ok"}
