# server_serene.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your chatbot functions
# (chatbot.py defines generate_reply(user_raw: str) -> str and assess_crisis(str) -> bool)
from chatbot import generate_reply, assess_crisis, CRISIS_MESSAGE

app = FastAPI(title="Serene.ai API", version="1.0")

# Allow calls from your local file / any origin during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatIn(BaseModel):
    text: str

class ChatOut(BaseModel):
    reply: str
    crisis: bool

@app.post("/v1/serene-chat", response_model=ChatOut)
def serene_chat(payload: ChatIn):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    is_crisis = assess_crisis(text)
    # If crisis, return the fixed safe message; else run normal generation
    reply = CRISIS_MESSAGE if is_crisis else generate_reply(text)
    return ChatOut(reply=reply, crisis=is_crisis)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server_serene:app", host="127.0.0.1", port=8000, reload=False)
