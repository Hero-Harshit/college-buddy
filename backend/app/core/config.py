import os
from typing import Tuple
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables (useful for local development)
load_dotenv()

def get_credentials() -> Tuple[str, str, str]:
    """
    Retrieves and validates required environment variables.
    Returns: (supabase_url, supabase_key, gemini_api_key)
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    missing = []
    if not supabase_url or supabase_url.startswith("your_"): 
        missing.append("SUPABASE_URL")
    if not supabase_key or supabase_key.startswith("your_"): 
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if not gemini_api_key or gemini_api_key.startswith("your_"): 
        missing.append("GEMINI_API_KEY")

    if missing:
        raise HTTPException(
            status_code=500, 
            detail=f"Missing required configuration: {', '.join(missing)}"
        )

    return supabase_url, supabase_key, gemini_api_key
