import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import json
# Load SETTINGS.json path configuration
SETTINGS = {}
try:
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SETTINGS.json")
    if os.path.exists(settings_path):
        with open(settings_path, "r") as f:
            SETTINGS = json.load(f)
except Exception as e:
    print(f"Warning: Failed to load SETTINGS.json: {e}")

STORIES_DIR = SETTINGS.get("STORIES_DIR", "stories")
SPECS_DIR = SETTINGS.get("SPECS_DIR", "specs")
FEATURES_DIR = SETTINGS.get("FEATURES_DIR", "features")
TOOLS_DIR = SETTINGS.get("TOOLS_DIR", "tools")

# Configuration variables
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Default models
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_OPENAI_MODEL = "gpt-4o"

LLM_MODEL = os.getenv("LLM_MODEL")
if not LLM_MODEL:
    LLM_MODEL = DEFAULT_GEMINI_MODEL if LLM_PROVIDER == "gemini" else DEFAULT_OPENAI_MODEL

# Validate API keys
def validate_config():
    if LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY is not set in environment or .env file.")
    elif LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY is not set in environment or .env file.")
    elif LLM_PROVIDER not in ["gemini", "openai"]:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}. Supported providers are 'gemini' and 'openai'.")

def get_gemini_client():
    from google import genai
    # Note: Client will automatically read GEMINI_API_KEY from environment if api_key is None
    return genai.Client(api_key=GEMINI_API_KEY)

def get_openai_client():
    from openai import OpenAI
    # Note: OpenAI will automatically read OPENAI_API_KEY from environment
    return OpenAI(api_key=OPENAI_API_KEY)

def get_llm_info():
    return {
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL
    }
