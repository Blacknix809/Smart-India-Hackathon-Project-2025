import os
from dotenv import load_dotenv

load_dotenv()

# Required
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Optional (comma-separated origins). If empty we’ll allow all in dev (see main.py).
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]

API_PREFIX = "/v1"
