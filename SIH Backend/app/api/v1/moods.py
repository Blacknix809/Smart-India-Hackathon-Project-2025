from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from app.core.db import pool

router = APIRouter()

class MoodIn(BaseModel):
    mood: str
    alias: str | None = None

    @field_validator("mood")
    @classmethod
    def check_mood(cls, v: str) -> str:
        if v not in ("happy", "neutral", "sad"):
            raise ValueError("mood must be happy|neutral|sad")
        return v

@router.post("/moods")
async def create_mood(m: MoodIn):
    if pool is None:
        raise HTTPException(500, "DB pool not initialized")
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "insert into moods (mood, alias) values (%s, %s) returning id::text, created_at::text",
                (m.mood, m.alias)
            )
            return await cur.fetchone()
