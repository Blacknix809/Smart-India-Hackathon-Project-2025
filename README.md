# Serene.ai – Student Mental Health Assistant

A full-stack AI-driven web application built for the **Smart India Hackathon (SIH)** to support students’ mental well-being through journaling, counseling, community sharing, meditation, and an empathetic chatbot powered by LLMs.

![Serene.ai Screenshot](docs/serene-preview.png)

---

## 🌟 Overview
Serene.ai offers students a safe digital space to:
- Express emotions privately (journals, mood tracking)
- Connect with peers (community posts)
- Seek help (counselor booking)
- Chat empathetically with an AI assistant (Serene)

Built with a modular architecture:
- **Frontend:** HTML, CSS, and vanilla JS  
- **Backend:** FastAPI (Python) with SQLite (default) or MySQL (for demo)  
- **Chatbot engine:** TinyLlama / Qwen models + FAISS retrieval + ALIVE empathy wrapper

> 🧩 **SIH Hackathon Note:** Firebase integration was originally planned for authentication and data storage.  
> Due to technical limitations at the venue, we used a **MySQL** backend for the live demo while retaining **SQLite** for local development.

---

## 🚀 Features

### 💬 Serene Chatbot
- Context-aware, empathetic responses using the ALIVE (Acknowledge–Label–Inquire–Validate–Explore) method.
- Crisis detection (keyword & NLI-based) with immediate helpline message.
- Uses FAISS + MiniLM for retrieval-augmented generation.

### 📘 Journal
- Personal notes stored locally (and synced to backend).
- Clean, distraction-free editor with autosave.
- Backend sync via `/v1/journal` API.

### 😊 Mood Tracker
- Emoji-based check-ins on the home screen.
- Auto-logs user mood via `/v1/moods` endpoint.
- Supports sentiment analytics and journaling suggestions.

### 👥 Community
- Anonymous or named sharing of posts.
- Trending topics sidebar.
- Local storage + backend sync for persistence.

### 🧘 Meditations & Mindfulness
- 12 guided meditations and coping audio placeholders.
- Simple, interactive cards with preview alerts.

### 🩺 Counseling Booking
- Integrated with counselor directory via `/v1/counselors` API.
- Dynamic Cal.com link redirection.
- One free consultation eligibility note.

---

## 🏗️ Architecture

```mermaid
flowchart TD
  subgraph Frontend
    A1[index.html]
    A2[login-signup.html]
    A3[serene-2.html]
    A4[community.html]
    A5[journal.html]
    A6[book.html]
    A7[meditations.html]
    A8[privacy.html]
    A9[script.js]
    A10[style.css]
  end

  subgraph Backend
    B1[app_sqlite_main.py]
    B2[chatbot.py]
    B3[server_serene.py]
    B4[/v1/moods]
    B5[/v1/journal]
    B6[/v1/posts]
    B7[/v1/counselors]
    B8[/v1/serene-chat]
  end

  subgraph Data
    D1[(SQLite / MySQL DB)]
    D2[(CSV Q&A Dataset)]
  end

  A3 --> B8
  A5 --> B5
  A4 --> B6
  A1 --> B4
  A6 --> B7
  B1 --> D1
  B2 --> D2
  B1 --> B4
  B1 --> B5
  B1 --> B6
  B1 --> B7
  B1 --> B8
```

---

## ⚙️ Backend Setup

```bash
# 1️⃣ Environment Setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U fastapi uvicorn pydantic pandas faiss-cpu torch sentence-transformers transformers

# 2️⃣ Run Backend (SQLite)
uvicorn app_sqlite_main:app --reload --port 8000

# 3️⃣ Run Chatbot-Only Server
python server_serene.py

# Access API docs
# http://127.0.0.1:8000/docs

# 4️⃣ Switching to MySQL (Optional)
# Update DB configuration in main.py → app.core.db
# Use aiomysql for async pooling
# (During the SIH demo, all data persisted via MySQL for stability)
```

---

## 💻 Frontend Setup

```bash
# 1️⃣ Open any .html file in the frontend/ folder using a live server (e.g., VS Code Live Server)
# 2️⃣ Ensure your backend runs locally at http://127.0.0.1:8000
# 3️⃣ (If needed) Update API_BASE constants inside .html files
# 4️⃣ Entry point: index.html
```

---

## 🔗 Backend API Endpoints

| Endpoint | Method | Description |
|-----------|--------|-------------|
| `/v1/health` | GET | Check server health |
| `/v1/counselors` | GET | Fetch list of counselors |
| `/v1/moods` | POST | Record a student’s mood |
| `/v1/journal` | GET / POST | Retrieve or save journal entries |
| `/v1/posts` | GET / POST | Retrieve or create community posts |
| `/v1/serene-chat` | POST | Get chatbot response |

---

## 🧠 Chatbot Stack
- **Embeddings:** SentenceTransformers (MiniLM-L6-v2)  
- **Retrieval:** FAISS (inner product)  
- **Reranker:** Cross-encoder (MS MARCO)  
- **LLM:** TinyLlama / Qwen 0.5B Instruct  
- **Empathy Engine:** ALIVE framework (dynamic templates)  
- **Crisis Detection:** Regex + Emotion classifier + safety message  

---

## 🛡️ Privacy & Safety
- Anonymous posting and journaling supported.  
- No personal data shared or stored externally.  
- Crisis messages include helpline numbers.  
- Privacy policy available in `privacy.html`.

---

## 🧩 Roadmap
- [ ] Firebase authentication & cloud storage (original plan)  
- [ ] Audio playback for meditations  
- [ ] Admin dashboard for counselor approval  
- [ ] LLM fine-tuning with domain-specific data  
- [ ] Responsive PWA + mobile-first UX  

---

## 🧾 Acknowledgments
- **Smart India Hackathon 2025** organizers & mentors  
- Open-source contributors from FastAPI, HuggingFace, and FAISS  
- **Team Serene** for design, research, and development  

---

## 📜 License
This project is licensed under the **MIT License**.  
See `LICENSE` for details.

---

**Developed with ❤️ for SIH 2025**  
_Made by Team Serene – Empowering students with mindful AI support._
