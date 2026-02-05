"""
Key Service - Fetches API keys from Supabase admin_api_keys table
All services should use this to get dynamic API keys
"""
import requests
from functools import lru_cache
from datetime import datetime, timedelta
from app.core.config import settings

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_KEY

# Cache for API keys
_key_cache: dict = {}
_cache_timestamp: datetime = None
CACHE_DURATION = timedelta(minutes=5)


def _fetch_all_keys() -> dict:
    """Fetch all API keys from Supabase."""
    global _key_cache, _cache_timestamp
    
    # Return cached if still valid
    if _cache_timestamp and (datetime.now() - _cache_timestamp) < CACHE_DURATION:
        return _key_cache
    
    try:
        url = f"{SUPABASE_URL}/rest/v1/admin_api_keys"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        params = {
            "select": "service_name,key_name,key_value,is_active",
            "is_active": "eq.true"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            keys = response.json()
            _key_cache = {}
            for key in keys:
                key_identifier = f"{key['service_name']}_{key['key_name']}"
                _key_cache[key_identifier] = key['key_value']
            _cache_timestamp = datetime.now()
            return _key_cache
    except Exception as e:
        print(f"Error fetching API keys: {e}")
    
    return _key_cache


def get_api_key(service_name: str, key_name: str, fallback: str = None) -> str:
    """
    Get a specific API key from the database.
    
    Args:
        service_name: The service name (e.g., 'gemini', 'serp', 'groq')
        key_name: The key name (e.g., 'GEMINI_API_KEY')
        fallback: Fallback value if key not found
        
    Returns:
        The API key value or fallback
    """
    keys = _fetch_all_keys()
    key_identifier = f"{service_name}_{key_name}"
    return keys.get(key_identifier) or fallback or ""


def get_gemini_key(fallback: str = None) -> str:
    """Get Gemini API key."""
    return get_api_key("gemini", "GEMINI_API_KEY", fallback)


def get_serp_key(fallback: str = None) -> str:
    """Get SERP API key."""
    return get_api_key("serp", "SERP_API_KEY", fallback)


def get_groq_key(fallback: str = None) -> str:
    """Get Groq API key."""
    return get_api_key("groq", "GROQ_API_KEY", fallback)


def get_github_client_id(fallback: str = None) -> str:
    """Get GitHub Client ID."""
    return get_api_key("github", "GITHUB_CLIENT_ID", fallback)


def get_github_client_secret(fallback: str = None) -> str:
    """Get GitHub Client Secret."""
    return get_api_key("github", "GITHUB_CLIENT_SECRET", fallback)


def get_aws_keys() -> tuple:
    """Get AWS access key and secret."""
    access_key = get_api_key("aws", "AWS_ACCESS_KEY_ID")
    secret_key = get_api_key("aws", "AWS_SECRET_ACCESS_KEY")
    return access_key, secret_key


def get_smtp_config() -> dict:
    """Get SMTP email configuration."""
    return {
        "host": get_api_key("email", "SMTP_HOST"),
        "port": int(get_api_key("email", "SMTP_PORT") or "587"),
        "user": get_api_key("email", "SMTP_USER"),
        "password": get_api_key("email", "SMTP_PASSWORD"),
        "from_email": get_api_key("email", "FROM_EMAIL")
    }


def clear_cache():
    """Clear the key cache."""
    global _key_cache, _cache_timestamp
    _key_cache = {}
    _cache_timestamp = None
