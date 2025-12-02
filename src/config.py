import os
from dotenv import load_dotenv

# Load local .env for development
load_dotenv()

def get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

def get_optional(key: str):
    return os.getenv(key)

# Required shared variables
SUPABASE_URL = get_required("SB_PROJECT_URL")
SUPABASE_ANON_KEY = get_required("SB_ANON_KEY")
PINECONE_API_KEY = get_required("PINECONE_API_KEY")

# Optional LLM provider keys
GEMINI_API_KEY = get_optional("GEMINI_API_KEY")
GROQ_API_KEY = get_optional("GROQ_API_KEY")
OPENROUTER_API_KEY = get_optional("OPENROUTER_API_KEY")
GEMINI_MODEL = get_optional("GEMINI_MODEL") or "gemini-pro?deploy"  # override at deploy time

# Decide provider priority: explicit preference order
# Uses GEMINI if present, else Groq, else OpenRouter
ACTIVE_LLM = None
if GEMINI_API_KEY:
    ACTIVE_LLM = ("gemini", GEMINI_MODEL, GEMINI_API_KEY)
elif GROQ_API_KEY:
    ACTIVE_LLM = ("claude", None, GROQ_API_KEY)
elif OPENROUTER_API_KEY:
    ACTIVE_LLM = ("openai", None, OPENROUTER_API_KEY)

if not ACTIVE_LLM:
    raise RuntimeError("No LLM configured: set GEMINI_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY")

# Expose for code
LLM_PROVIDER, LLM_MODEL, LLM_KEY = ACTIVE_LLM
