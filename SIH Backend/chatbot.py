# ================== IMPORTS ==================
import os, re, sys, random, string, smtplib
from collections import deque
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification, pipeline

# ================== CONFIG ==================
CSV_PATH = r"C:\Users\HP\OneDrive\Desktop\SIH Backend\expanded_student_mental_health_chatbot.csv"

PRIMARY_LLM  = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
FALLBACK_LLM = "Qwen/Qwen2.5-0.5B-Instruct"

EMBED_MODEL    = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

K_RETRIEVE       = 6
K_RERANK         = 2
USE_RERANKER     = True
MAX_INPUT_TOKENS = 1024
MAX_NEW_TOKENS   = 150

# Trusted contacts for crisis email alerts
TRUSTED_CONTACTS = ["Kartikagrawal0725@gmail.com", "sohachand@yahoo.com"]
EMAIL_SENDER = "sparktn455@gmail.com"
EMAIL_PASSWORD = "dptizhfreljcsitm"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

CRISIS_MESSAGE = (
    "I’m really glad you told me. Your safety matters. "
    "If you’re in immediate danger, please contact local emergency services. "
    "Would you like resources for your area?"
)

# ================== LOAD CSV ==================
if not os.path.exists(CSV_PATH):
    print(f"CSV not found: {CSV_PATH}", file=sys.stderr)
    sys.exit(1)

df = pd.read_csv(CSV_PATH)
for col in ("user_input", "bot_response"):
    if col not in df.columns:
        print(f"CSV must include '{col}' column.", file=sys.stderr)
        sys.exit(1)

df["user_input"]  = df["user_input"].astype(str).str.strip().str.lower()
df["bot_response"] = df["bot_response"].astype(str).str.strip()
if "emotion_tag" in df.columns:
    df["emotion_tag"] = df["emotion_tag"].astype(str).str.strip().str.lower()
else:
    df["emotion_tag"] = "neutral"

docs = [{"q": q, "a": a, "emotion": emo}
        for q, a, emo in zip(df["user_input"], df["bot_response"], df["emotion_tag"])]

# ================== EMBEDDINGS ==================
embedder = SentenceTransformer(EMBED_MODEL)
dim = embedder.get_sentence_embedding_dimension()
import faiss
index = faiss.IndexFlatIP(dim)
queries = [d["q"] for d in docs]
embs = embedder.encode(queries, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
index.add(embs)

# ================== RERANKER ==================
if USE_RERANKER:
    reranker = CrossEncoder(RERANKER_MODEL)

# ================== LLM ==================
def load_llm():
    for name in (PRIMARY_LLM, FALLBACK_LLM):
        try:
            tok = AutoTokenizer.from_pretrained(name, trust_remote_code=True)
            mdl = AutoModelForCausalLM.from_pretrained(
                name,
                trust_remote_code=True,
                device_map="cpu",
                low_cpu_mem_usage=True,
                attn_implementation="eager",
            )
            if tok.pad_token is None:
                tok.pad_token = tok.eos_token
            print(f"[LLM] Loaded: {name}")
            return tok, mdl
        except Exception as e:
            print(f"[LLM] Could not load {name}: {e}\nTrying fallback...", file=sys.stderr)
    print("[LLM] Failed to load any model.", file=sys.stderr)
    sys.exit(1)

tokenizer, model = load_llm()

# ================== CONVERSATION MEMORY ==================
history = deque(maxlen=6)
def add_to_history(u, b): history.append((u, b))
def history_block(): return "\n".join([f"User: {u}\nAssistant: {b}" for u, b in history])

# ================== TEMPLATES ==================
ACK_TEMPLATES = [
    "I’m hearing how {focus} is weighing on you.",
    "Thanks for sharing—{focus} sounds like a lot to carry.",
    "That’s a lot: {focus}.",
    "It makes sense that {focus} would feel intense."
]
VALIDATE_TEMPLATES = [
    "Your feelings are valid—many students feel this in similar situations.",
    "It’s understandable to feel this way with so much on your plate.",
    "You’re not overreacting—what you’re facing would challenge anyone.",
    "It’s okay to feel like this; it doesn’t mean you’re failing."
]
INQUIRE_TEMPLATES = [
    "What part of this feels hardest right now?",
    "If we zoom in—what’s the next small thing worrying you?",
    "When does it spike the most—at night, before class, or while studying?",
    "What’s one thing that, if easier, would help the most today?"
]
EXPLORE_TEMPLATES = [
    "We can try one small step: a 5-minute pause, a quick plan for the next hour, or a gentle walk—what sounds doable?",
    "Let’s pick a tiny action—2 minutes of slow breathing, a short checklist, or reaching out to a friend.",
    "How about a micro-step: write 3 tasks for the next hour, take 10 slow breaths, or get a glass of water first?",
    "Would a short reset help—sip water, stretch, then one 15-minute study block?"
]

_last_opening = None
_last_validation = None
def _choose(template_list, which):
    global _last_opening, _last_validation
    last = _last_opening if which == "opening" else _last_validation
    pool = [t for t in template_list if t != last] or template_list
    choice = random.choice(pool)
    if which == "opening": _last_opening = choice
    else: _last_validation = choice
    return choice

# ================== CRISIS / SENTIMENT MODEL ==================
sentiment_model_name = "j-hartmann/emotion-english-distilroberta-base"
sentiment_tokenizer = AutoTokenizer.from_pretrained(sentiment_model_name)
sentiment_model = AutoModelForSequenceClassification.from_pretrained(sentiment_model_name)
sentiment_pipe = pipeline(
    "text-classification",
    model=sentiment_model,
    tokenizer=sentiment_tokenizer,
    device=-1,  # If you added this earlier
    top_k=None  # Replaces return_all_scores=True (no warning)
)


# Add this right after sentiment_pipe = ... (before def assess_crisis)
HARM_KEYWORDS = [
    "suicide", "kill myself", "hurt myself", "self-harm", "cut myself", "die", "overdose",
    "end it all", "no longer want to live", "give up on life", "want to suicide"  # Added for your exact input
]

def assess_crisis(user_text: str) -> bool:
    if not user_text.strip():
        return False
    
    user_lower = user_text.lower().strip()
    # Keyword fallback (keep as-is)
    if any(kw in user_lower for kw in HARM_KEYWORDS):
        return True
    
    # Sentiment fallback: Ultra-high thresholds
    scores = sentiment_pipe(user_text)
    sadness_score = fear_score = 0.0
    for s in scores[0]:
        if s['label'].lower() == "sadness":
            sadness_score = s['score']
        elif s['label'].lower() == "fear":
            fear_score = s['score']
    
    # Extreme-only triggers
    if (sadness_score > 0.98) or \
       (sadness_score > 0.95 and fear_score > 0.8) or \
       (fear_score > 0.98):
        return True
    
    return False




def send_crisis_email(user_text: str):
    email_sent = False
    for contact in TRUSTED_CONTACTS:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = contact
        msg["Subject"] = "CRISIS ALERT from Student Chatbot"
        body = f"The chatbot detected a crisis message:\n\n{user_text}"
        msg.attach(MIMEText(body, "plain"))
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            email_sent = True  # Mark as sent if at least one succeeds
        except:
            pass  # Silent error handling (retry logic if needed later)
    
    if email_sent:
        print("Email sent to contacts.")


# ================== FEELINGS + ALIVE WRAP ==================
STOPWORDS = set([
    "i","im","i'm","am","is","are","was","were","a","an","the","and","or","but","so","to","of","in","on","at",
    "for","with","about","as","that","this","it","its","it's","be","been","being","do","does","did","can","could",
    "should","would","will","shall","have","has","had","you","your","yours","me","my","mine","we","our","ours",
    "they","them","their","theirs","he","she","his","her","him","from","by","if","than","then","when","while",
    "because","though","although","just","really","very","too","also","still"
])

# ================== FEELINGS + ALIVE WRAP ==================
# Expanded feelings dict: More accurate for student contexts
FEELINGS = {
    "stressed": "stressed",
    "anxious": "anxious",
    "overwhelmed": "overwhelmed",
    "tired": "exhausted",
    "sad": "sad",
    "upset": "upset",
    "angry": "frustrated",
    "scared": "fearful",
    "worried": "worried",
    "happy": "positive",
    "excited": "excited",
    "calm": "calm",
    "exams": "stressed",  # Context-specific
    "study": "overwhelmed",
    "fail": "anxious"
}

def infer_feeling(text: str) -> str:
    text_lower = text.lower()
    for key, feeling in FEELINGS.items():
        if key in text_lower:
            return feeling
    return "overwhelmed"  # Default for unknowns (common in student chats)

def salient_phrases(text: str, max_terms: int = 2) -> list:
    text_lower = text.lower()
    # Expanded regex: More student-relevant terms (nouns/phrases)
    phrases = re.findall(r'\b(?:stressed|anxious|exams|study|tips|fail|pass|sleep|relationship|motivation|upcoming|properly)\b', text_lower)
    unique_phrases = list(dict.fromkeys(phrases))[:max_terms]
    return unique_phrases if unique_phrases else ["your challenge"]

def alive_wrap(user_text: str, model_reply: str) -> str:
    user_lower = user_text.lower()
    # Skip harm check if crisis (but since crises use CRISIS_MESSAGE, this is for normals)
    if any(kw in user_lower for kw in ["suicide", "hurt", "die", "kill"]):
        focus = "what you're going through"  # Safe
    else:
        feeling = infer_feeling(user_text)
        focus_terms = salient_phrases(user_text)
        focus = ", ".join(focus_terms) if len(focus_terms) > 1 else focus_terms[0] if focus_terms else "your situation"
    
    # Warmer templates: More empathetic, student-focused
    opening  = random.choice([  # Varied openings
        f"I hear how {focus} is weighing on you right now.",
        f"It's tough when {focus} feels so heavy—I'm here with you.",
        f"Thanks for sharing about {focus}. That sounds really challenging."
    ])
    label    = f"It sounds like you're feeling {feeling} about this."  # More natural
    inquire  = random.choice([  # Specific inquiries
        "What part of this feels the hardest for you?",
        "How has this been affecting your day?",
        "Would you like some ideas to make it a bit easier?"
    ])
    validate = random.choice([  # Stronger validation
        "It's completely valid to feel this way—many students do.",
        "You're not alone in this; it's okay to struggle.",
        "Taking a moment to acknowledge this is a strong step."
    ])
    explore  = random.choice([  # Gentle exploration
        "We can break it down together if you'd like.",
        "Small steps can help—want to try one?",
        "I'm listening without judgment."
    ])
    
    # Combine: Opening + Label + LLM + Inquire/Validate/Explore (shorter for flow)
    text = f"{opening} {label} {model_reply.strip()}. {inquire} {validate} {explore}"
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:5]).strip()  # Slightly longer (5 sentences) for completeness, no abrupt "..."


# ================== CONTEXT RETRIEVAL ==================
def retrieve_context(query: str, k_retrieve=K_RETRIEVE, k_rerank=K_RERANK):
    qv = embedder.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
    D, I = index.search(qv, k_retrieve)
    cand = [docs[i] for i in I[0] if 0 <= i < len(docs)]
    if not cand: return []
    if not USE_RERANKER: return cand[:k_rerank]
    pairs  = [(query, c["q"]) for c in cand]
    scores = reranker.predict(pairs)
    reranked = sorted(zip(cand, scores), key=lambda x: x[1], reverse=True)
    return [c for c, _ in reranked[:k_rerank]]

def build_context_block(cands):
    return "\n".join([f"- USER said: {c['q']}\n  BOT replied: {c['a']}" for c in cands])

# ================== EXIT COMMANDS ==================
exit_commands = [
    "bye", "goodbye", "quit", "exit", "cya", "see you", "farewell",
    "i am done", "i'm done", "done", "later", "talk to you soon",
    "good night", "take care", "leave", "i’m leaving",
    "see ya", "thanks bye", "ok bye"
]

# ================== BOT GENERATION ==================
def generate_reply(user_raw: str):
    if assess_crisis(user_raw):
        send_crisis_email(user_raw)
        print("Bot:", CRISIS_MESSAGE)
        add_to_history(user_raw, CRISIS_MESSAGE)
        return CRISIS_MESSAGE

    # Greeting
    if re.match(r"^(hi|hello|hey|yo|hiya|hii+|good\s*(morning|afternoon|evening))\b", user_raw.strip(), re.I):
        reply = "Hi! I’m here for you. What would you like to talk about—study stress, motivation, sleep, relationships, or something else?"
        print("Bot:", reply)
        add_to_history(user_raw, reply)
        return reply

    # Retrieve context
    top_docs = retrieve_context(user_raw)
    context  = build_context_block(top_docs)
    mem      = history_block()
    system = "You are a warm, empathetic student mental health assistant. Your role is to support college/university students with everyday challenges like academic stress, relationships, sleep issues, motivation, and mild anxiety. Always start by validating their feelings (e.g., 'That sounds really tough—I get why you'd feel overwhelmed'), reflect key details from their message, and offer 1-2 gentle, practical suggestions tailored to student life (e.g., quick study hacks for exams, breathing exercises for anxiety, or journaling for emotions). Keep responses hopeful, encouraging, and 4-6 sentences long—focus on empowerment and small steps rather than overwhelming plans. End every reply with an open question to invite more sharing (e.g., 'What's one thing that's helped before?' or 'How are you feeling about that?'). Be conversational and friendly, like a supportive peer—use emojis sparingly (e.g., 💙 for care) and avoid clinical language, diagnoses, or dismissive phrases like 'just relax.' If the user mentions harm or crisis, respond supportively but urge professional help (e.g., 'Please reach out to a hotline—I'm here to listen too'). Do not role-play, use tags, or go off-topic. Examples: - User: 'I'm so stressed about finals.' → 'I hear how finals are piling up—that pressure is real for so many students. It's okay to feel this way; you're not alone. One thing that helps is the Pomodoro technique: study for 25 minutes, then take a 5-minute break to stretch or breathe. Remember, you've gotten through tough times before. What subject is stressing you most right now? 💙' - User: 'I can't sleep because of worries.' → 'Sleep troubles from worries sound exhausting—it's common during busy semesters. Validating that: your mind is probably racing with everything on your plate. Try a simple wind-down routine, like dimming lights 30 minutes before bed and listing three things you're grateful for. This can quiet the thoughts a bit. How long has this been going on for you?'"
    # At the end of system = "..."
    system += " For anxiety mentions, always validate first (e.g., 'Anxiety can feel overwhelming, but it's a signal to pause') and suggest quick tools like 4-7-8 breathing or grounding exercises before deeper tips."
    prompt   = f"<system>{system}</system>\n<context>{context}</context>\n<history>{mem}</history>\nUser: {user_raw}\nAssistant:"

    inputs  = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=MAX_INPUT_TOKENS)
    gen_kwargs = dict(
    max_new_tokens=150,  # Increased: Longer, more detailed replies
    do_sample=True,
    temperature=0.7,  # Slightly higher: More natural/varied (less robotic)
    top_p=0.9,
    repetition_penalty=1.15,  # Slightly higher: Reduces repeats
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.eos_token_id,
)


    try:
      outputs = model.generate(**inputs, **gen_kwargs)
      full  = tokenizer.decode(outputs[0], skip_special_tokens=True)
      raw_reply = full[len(prompt):].strip()
      
      # Enhanced regex: Strip more tag patterns (User/Assistant/System, XML, end tags, extra newlines)
      raw_reply = re.split(r"\n(?:User|Assistant|System|\<\/?[\w\s]>)\s:?", raw_reply, maxsplit=1, flags=re.I)[0].strip()
      raw_reply = re.sub(r"<\/?[\w\s]*>", "", raw_reply)  # Remove any remaining XML/end tags
      raw_reply = re.sub(r"\n{2,}", " ", raw_reply)  # Collapse multiple newlines
      raw_reply = raw_reply.strip()
    except Exception as e:
      print(f"[LLM ERROR] Generation failed: {e}. Using fallback.", file=sys.stderr)
      raw_reply = "I'm here to listen and support you. What's on your mind?"


    if len(raw_reply) < 3 or raw_reply.lower() in {"hi","hello","hey"}:
        raw_reply = "Thanks for sharing. What feels toughest right now? We can take it one small step at a time."

    final = alive_wrap(user_raw, raw_reply)
    print("Bot:", final)
    add_to_history(user_raw, final)
    return final

# ================== MAIN LOOP ==================
if __name__ == "__main__":
    print("Bot: Hi! I'm here to listen and support you—no judgment. What's on your mind today? 💙")
    while True:
        try:
            user = input("User: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot: Goodbye! Take care 💙")
            break

        # Exit check
        user_words = set(re.findall(r"\b\w+\b", user.lower()))
        if user_words & set(exit_commands):
            print("Bot: Goodbye! Take care 💙")
            break

        generate_reply(user)