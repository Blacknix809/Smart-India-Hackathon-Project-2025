from fastapi import APIRouter, HTTPException
from app.core.db import pool

router = APIRouter()

@router.get("/counselors")
async def list_counselors():
    if pool is None:
        raise HTTPException(500, "DB pool not initialized")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                select id::text, name, specialty, languages, bio, cal_link
                from counselors
                where visible = true
                order by name
            """)
            return await cur.fetchall()
