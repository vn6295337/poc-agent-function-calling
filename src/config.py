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
OPENAI_API_KEY = get_optional("OPENAI_API_KEY")
CLAUDE_API_KEY = get_optional("CLAUDE_API_KEY")

# Must have at least 1 LLM provider
if not (OPENAI_API_KEY or CLAUDE_API_KEY):
    raise RuntimeError("Either OPENAI_API_KEY or CLAUDE_API_KEY must be set.")
