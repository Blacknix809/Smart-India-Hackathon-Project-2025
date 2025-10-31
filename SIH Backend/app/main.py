from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import psycopg
from psycopg.rows import dict_row
from psycopg import errors as pg_errors
from dotenv import load_dotenv

# ---- load environment (.env) ----
load_dotenv()

# ---- app ----
app = FastAPI(title="Student Support API")

# Allow everything for dev; tighten in prod by setting specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DB Helpers ----------
def _normalized_db_url() -> str:
    """Return DATABASE_URL with ssl + timeout appended safely."""
    url = (os.getenv("DATABASE_URL") or "postgresql://postgres:password@localhost:5432/postgres").strip()

    # Ensure sslmode=require for Supabase-like hosts
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"

    # Ensure a fast connect timeout so requests don't hang forever
    if "connect_timeout=" not in url:
        url += ("&" if "?" in url else "?") + "connect_timeout=5"

    return url

def get_conn():
    """Open a psycopg connection with dict rows and fast failure."""
    url = _normalized_db_url()
    try:
        return psycopg.connect(url, row_factory=dict_row)
    except Exception as e:
        # Surface connection problems clearly
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")

def _fetchall(sql: str, params: tuple | None = None):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()
    except pg_errors.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _fetchone(sql: str, params: tuple | None = None):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                return cur.fetchone()
    except pg_errors.Error as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Health ----------
@app.get("/v1/healthz")
def healthz():
    # instant, doesn’t touch DB
    return {"status": "ok"}

@app.get("/v1/dbcheck")
def dbcheck():
    try:
        row = _fetchone("select 1 as ok;")
        return {"db": row["ok"], "status": "ok"}
    except HTTPException as e:
        # Return a JSON error payload so you can see the root cause quickly
        return {"db": "error", "error": e.detail}

# ---------- Counselors ----------
@app.get("/v1/counselors")
def get_counselors():
    # Prefer visible=true, but if column doesn't exist, fall back gracefully
    try:
        rows = _fetchall(
            "select id::text, name, specialty, languages, bio, cal_link "
            "from counselors where visible=true order by name"
        )
        return rows
    except HTTPException as e:
        if "column \"visible\" does not exist" in str(e.detail).lower():
            return _fetchall(
                "select id::text, name, specialty, languages, bio, cal_link "
                "from counselors order by name"
            )
        raise

# ---------- Moods ----------
class MoodIn(BaseModel):
    mood: str
    alias: str | None = None

@app.post("/v1/moods")
def create_mood(m: MoodIn):
    if m.mood not in ("happy", "neutral", "sad"):
        raise HTTPException(status_code=400, detail="Invalid mood")
    row = _fetchone(
        "insert into moods (mood, alias) values (%s,%s) "
        "returning id::text, created_at::text",
        (m.mood, m.alias),
    ) 
    return row

# ---------- Journal ----------
class JournalIn(BaseModel):
    user_alias: str
    text: str

@app.post("/v1/journal")
def add_entry(j: JournalIn):
    row = _fetchone(
        "insert into journal_entries (user_alias, text) values (%s,%s) "
        "returning id::text, user_alias, text, created_at::text",
        (j.user_alias, j.text),
    )
    return row

@app.get("/v1/journal")
def list_entries(user_alias: str):
    rows = _fetchall(
        "select id::text, user_alias, text, created_at::text "
        "from journal_entries where user_alias=%s order by created_at desc",
        (user_alias,),
    )
    return rows

# ---------- Posts ----------
class PostIn(BaseModel):
    category: str
    body: str
    anon: bool = True
    alias: str | None = None

@app.post("/v1/posts")
def create_post(p: PostIn):
    if len(p.body) < 10:
        raise HTTPException(status_code=400, detail="Post too short")
    row = _fetchone(
        "insert into posts (category, body, anon, alias, status) "
        "values (%s,%s,%s,%s,'pending') returning id::text, status",
        (p.category, p.body, p.anon, p.alias),
    )
    return row

@app.get("/v1/posts")
def list_posts(status: str = "live"):
    rows = _fetchall(
        "select id::text, category, body, anon, alias, created_at::text "
        "from posts where status=%s order by created_at desc",
        (status,),
    )
    return rows
