from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import re
from app.core.db import pool

router = APIRouter()

# very light PII check (you still keep status pending in UI logic)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b[0-9]{10}\b")
ROLL_RE  = re.compile(r"\b\d{7,}\b")

class PostIn(BaseModel):
    category: str
    body: str
    anon: bool = True
    alias: str | None = None

@router.post("/posts")
async def create_post(p: PostIn):
    if len(p.body) < 10 or len(p.body) > 2000:
        raise HTTPException(400, "Post length must be between 10 and 2000 characters")

    _ = EMAIL_RE.search(p.body) or PHONE_RE.search(p.body) or ROLL_RE.search(p.body)

    if pool is None:
        raise HTTPException(500, "DB pool not initialized")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                insert into posts (category, body, anon, alias, status)
                values (%s, %s, %s, %s, 'pending')
                returning id::text, status
                """,
                (p.category, p.body, p.anon, p.alias)
            )
            return await cur.fetchone()

@router.get("/posts")
async def list_posts(status: str = Query("live")):
    if status not in ("live", "pending", "removed"):
        raise HTTPException(400, "invalid status")
    if pool is None:
        raise HTTPException(500, "DB pool not initialized")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                select id::text, category, body, anon, alias, created_at::text
                from posts
                where status = %s
                order by created_at desc
                """,
                (status,)
            )
            return await cur.fetchall()
