from supabase import create_client, Client
from app.core.config import get_credentials

_supabase_client: Client | None = None

def get_supabase_client() -> Client:
    """
    Returns a singleton instance of the Supabase client.
    """
    global _supabase_client
    if _supabase_client is None:
        supabase_url, supabase_key, _ = get_credentials()
        _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client
