# app_serene.py
import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# IMPORTANT: set path to your CSV if you don't want to edit chatbot.py
# os.environ["CHATBOT_CSV_PATH"] = r"C:\path\to\expanded_student_mental_health_chatbot.csv"

# Import your chatbot (this will load embeddings + models on import)
import chatbot  # your file name, same folder

app = FastAPI(title="Serene Chat API")

# CORS open for dev (tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatIn(BaseModel):
    text: str
    alias: Optional[str] = None  # if you want to pass a name from front-end

class ChatOut(BaseModel):
    reply: str
    crisis: bool

@app.get("/v1/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/v1/serene-chat", response_model=ChatOut)
def serene_chat(body: ChatIn):
    user_text = (body.text or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="text is required")

    # Optional: check crisis separately so you can mark the response
    is_crisis = False
    try:
        is_crisis = chatbot.assess_crisis(user_text)
    except Exception:
        is_crisis = False

    try:
        reply = chatbot.generate_reply(user_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"chatbot error: {e}")

    return ChatOut(reply=reply, crisis=is_crisis)
