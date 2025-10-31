from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.core.db import pool

router = APIRouter()

class JournalIn(BaseModel):
    user_alias: str
    text: str

@router.post("/journal")
async def create_entry(j: JournalIn):
    if pool is None:
        raise HTTPException(500, "DB pool not initialized")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into journal_entries (user_alias, text)
                values (%s, %s)
                returning id::text, user_alias, text, created_at::text
                """,
                (j.user_alias, j.text)
            )
            return await cur.fetchone()

@router.get("/journal")
async def list_entries(user_alias: str = Query(...)):
    if pool is None:
        raise HTTPException(500, "DB pool not initialized")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select id::text, user_alias, text, created_at::text
                from journal_entries
                where user_alias = %s
                order by created_at desc
                """,
                (user_alias,)
            )
            return await cur.fetchall()
