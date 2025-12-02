import os
from dotenv import load_dotenv

# Load .env for local development (ignored in Cloud Run)
load_dotenv()

def get(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

# Unified env accessor
SUPABASE_URL = get("SB_PROJECT_URL")
SUPABASE_ANON_KEY = get("SB_ANON_KEY")
PINECONE_API_KEY = get("PINECONE_API_KEY")
OPENAI_API_KEY = get("OPENAI_API_KEY")
CLAUDE_API_KEY = get("CLAUDE_API_KEY")
