# app_sqlite_main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3, os, importlib
from typing import Optional

# ---------- App & CORS ----------
DB_PATH = os.getenv("SQLITE_DB", "demo.db")

app = FastAPI(
    title="Student Support API (SQLite)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Chatbot: lazy loader (avoids blocking /docs on startup) ----------
_CHATBOT = {
    "loaded": False,
    "generate_reply": None,
    "assessor": None,          # assess_risk or assess_crisis
    "CRISIS_MESSAGE": None,
}

def _load_chatbot():
    """Import chatbot on first use; cache functions. Return None on success, str on error."""
    if _CHATBOT["loaded"]:
        return None
    try:
        mod = importlib.import_module("chatbot")  # chatbot.py must be on PYTHONPATH / same folder
    except Exception as e:
        return f"cannot import chatbot: {e}"

    # prefer assess_risk; fall back to assess_crisis
    generate_reply = getattr(mod, "generate_reply", None)
    assess_risk    = getattr(mod, "assess_risk", None)
    assess_crisis  = getattr(mod, "assess_crisis", None)
    crisis_msg     = getattr(mod, "CRISIS_MESSAGE", None)

    if generate_reply is None:
        return "chatbot.generate_reply not found"

    assessor = assess_risk or assess_crisis
    if assessor is None:
        return "chatbot assess function not found (need assess_risk or assess_crisis)"

    if crisis_msg is None:
        # a safe default if not provided by chatbot.py
        crisis_msg = (
            "I’m really glad you told me. Your safety matters. "
            "If you’re in immediate danger, please contact local emergency services. "
            "You can also call 1800-599-0019 to talk to someone now."
        )

    _CHATBOT.update(
        loaded=True,
        generate_reply=generate_reply,
        assessor=assessor,
        CRISIS_MESSAGE=crisis_msg,
    )
    return None

def _is_crisis(val) -> bool:
    """Normalize assessor outputs to bool."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in {"high", "medium", "true", "yes"}
    try:
        return bool(val)
    except Exception:
        return False

# ---------- DB helpers ----------
def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn

def _fetchall(sql, params=()):
    with _get_conn() as conn:
        cur = conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

def _fetchone(sql, params=()):
    with _get_conn() as conn:
        cur = conn.execute(sql, params)
        r = cur.fetchone()
        return dict(r) if r else None

def _execute(sql, params=()):
    with _get_conn() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid

# ---------- health / dbcheck ----------
@app.get("/v1/health")
def health():
    return {"ok": True}

@app.get("/v1/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/v1/dbcheck")
def dbcheck():
    try:
        r = _fetchone("SELECT 1 AS ok")
        return {"db": r["ok"], "status": "ok"}
    except Exception as e:
        return {"db": "error", "error": str(e)}

# ---------- counselors ----------
@app.get("/v1/counselors")
def get_counselors():
    return _fetchall(
        "SELECT id, name, specialty, languages, bio, cal_link "
        "FROM counselors WHERE visible=1 ORDER BY name"
    )

# ---------- moods ----------
class MoodIn(BaseModel):
    mood: str
    alias: Optional[str] = None

@app.post("/v1/moods")
def create_mood(m: MoodIn):
    allowed = {"happy", "calm", "neutral", "sad", "anxious"}
    if m.mood not in allowed:
        raise HTTPException(400, "Invalid mood")
    rowid = _execute(
        "INSERT INTO moods (mood, alias) VALUES (?, ?)",
        (m.mood, m.alias),
    )
    return _fetchone(
        "SELECT id, mood, alias, created_at FROM moods WHERE id=?",
        (rowid,),
    )

# ---------- journal ----------
class JournalIn(BaseModel):
    user_alias: str
    text: str

@app.post("/v1/journal")
def add_entry(j: JournalIn):
    rowid = _execute(
        "INSERT INTO journal_entries (user_alias, text) VALUES (?, ?)",
        (j.user_alias, j.text),
    )
    return _fetchone(
        "SELECT id, user_alias, text, created_at FROM journal_entries WHERE id=?",
        (rowid,),
    )

@app.get("/v1/journal")
def list_entries(user_alias: str):
    return _fetchall(
        "SELECT id, user_alias, text, created_at "
        "FROM journal_entries WHERE user_alias=? ORDER BY created_at DESC",
        (user_alias,),
    )

# ---------- posts ----------
class PostIn(BaseModel):
    category: str
    body: str
    anon: bool = True
    alias: Optional[str] = None

@app.post("/v1/posts")
def create_post(p: PostIn):
    if len(p.body) < 10:
        raise HTTPException(400, "Post too short")
    rowid = _execute(
        "INSERT INTO posts (category, body, anon, alias, status) "
        "VALUES (?,?,?,?, 'pending')",
        (p.category, p.body, int(p.anon), p.alias),
    )
    return _fetchone("SELECT id, status FROM posts WHERE id=?", (rowid,))

@app.get("/v1/posts")
def list_posts(status: str = "live"):
    return _fetchall(
        "SELECT id, category, body, anon, alias, created_at "
        "FROM posts WHERE status=? ORDER BY created_at DESC",
        (status,),
    )

# ---------- serene chat ----------
class ChatIn(BaseModel):
    text: str

@app.post("/v1/serene-chat")
def serene_chat(payload: ChatIn):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    err = _load_chatbot()
    if err:
        raise HTTPException(status_code=503, detail=f"chatbot not ready: {err}")

    crisis_val = _CHATBOT["assessor"](text)
    crisis = _is_crisis(crisis_val)

    if crisis:
        reply = _CHATBOT["CRISIS_MESSAGE"]
    else:
        reply = _CHATBOT["generate_reply"](text)

    return {"reply": reply, "crisis": crisis}
