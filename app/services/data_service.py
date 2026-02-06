"""
Data Service - Fetches all required data from Supabase for skill gap analysis
"""
import requests
from app.core.config import settings
from datetime import datetime, timezone

SUPABASE_REST_URL = f"{settings.SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": settings.SUPABASE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def get_user_profile(user_id: str) -> dict:
    """Get user profile data."""
    url = f"{SUPABASE_REST_URL}/profiles?id=eq.{user_id}&select=*"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200 and response.json():
        return response.json()[0]
    return {}


def get_user_preferred_roles(user_id: str) -> list[str]:
    """Get user's preferred job roles (up to 3)."""
    url = f"{SUPABASE_REST_URL}/user_preferred_roles?user_id=eq.{user_id}&select=role_name&order=priority.asc"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200 and response.json():
        return [r["role_name"] for r in response.json()]
    return []


def get_user_skills(user_id: str) -> list[dict]:
    """Get user's skills from resume and GitHub."""
    url = f"{SUPABASE_REST_URL}/user_skills?user_id=eq.{user_id}&select=skill_name,source,proficiency_level,confidence_score,source_repo"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    return []


def get_skill_trends(limit: int = 30) -> list[dict]:
    """Get current skill trends from the trend service data."""
    url = f"{SUPABASE_REST_URL}/skill_trends?select=skill_name,job_mention_count,discussion_mention_count,trend_direction&order=job_mention_count.desc&limit={limit}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    return []


def get_recent_jobs(limit: int = 50) -> list[dict]:
    """Get recently fetched jobs for market analysis."""
    url = f"{SUPABASE_REST_URL}/fetched_jobs?select=title,company_name,description,work_type,experience_level&order=fetched_at.desc&limit={limit}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    return []


def get_recent_discussions(limit: int = 30) -> list[dict]:
    """Get recent Reddit discussions."""
    url = f"{SUPABASE_REST_URL}/fetched_discussions?select=title,body,subreddit,upvotes,comments_count&order=upvotes.desc&limit={limit}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    return []


def store_analysis_result(
    user_id: str,
    preferred_roles: list[str],
    analysis: dict
) -> str:
    """Store the analysis result in skill_gap_analyses table."""
    
    # Prepare data for insertion
    analysis_data = {
        "user_id": user_id,
        "target_job_title": ", ".join(preferred_roles),
        "model_version": analysis.get("model_used", "gemini-2.5-pro"),
        "gap_percentage": analysis.get("overall_gap_percentage", 0),
        "role_fit_score": analysis.get("overall_fit_score", 0),
        "matched_skills": analysis.get("skill_assessment", {}).get("strong_skills", []),
        "missing_skills": [s.get("skill") for s in analysis.get("critical_missing_skills", [])],
        "partial_skills": analysis.get("skill_assessment", {}).get("needs_improvement", []),
        "recommendations": analysis.get("recommendations", {}),
        "market_demand_score": analysis.get("competitiveness_scores", [{}])[0].get("score", 0) if analysis.get("competitiveness_scores") else 0,
        "trend_direction": "stable",
        "status": "completed",
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }
    
    url = f"{SUPABASE_REST_URL}/skill_gap_analyses"
    headers = {**HEADERS, "Prefer": "return=representation"}
    
    response = requests.post(url, headers=headers, json=analysis_data, timeout=10)
    
    if response.status_code in [200, 201] and response.json():
        return response.json()[0].get("id", "")
    
    print(f"Error storing analysis: {response.text}")
    return ""


def store_report_record(
    user_id: str,
    analysis_id: str,
    report_filename: str,
    report_url: str,
    report_size: int
) -> str:
    """Store the report record in reports table."""
    
    report_data = {
        "user_id": user_id,
        "analysis_id": analysis_id,
        "report_filename": report_filename,
        "report_url": report_url,
        "report_size_bytes": report_size,
        "report_type": "skill_gap_analysis",
        "status": "generated",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    
    url = f"{SUPABASE_REST_URL}/reports"
    headers = {**HEADERS, "Prefer": "return=representation"}
    
    response = requests.post(url, headers=headers, json=report_data, timeout=10)
    
    if response.status_code in [200, 201] and response.json():
        return response.json()[0].get("id", "")
    
    print(f"Error storing report record: {response.text}")
    return ""


def get_all_users_for_cron() -> list[dict]:
    """Get all users who should receive weekly reports."""
    # Get users with notification_interval = 'weekly' and have connected GitHub or uploaded resume
    url = f"{SUPABASE_REST_URL}/profiles?select=id,email,full_name&or=(github_username.neq.null,resume_url.neq.null)"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return response.json()
    return []


def set_preferred_roles(user_id: str, roles: list[str]) -> dict:
    """Set or update user's preferred roles (max 3)."""
    # First delete existing roles
    delete_url = f"{SUPABASE_REST_URL}/user_preferred_roles?user_id=eq.{user_id}"
    requests.delete(delete_url, headers=HEADERS, timeout=10)
    
    # Insert new roles
    inserted = []
    for i, role in enumerate(roles[:3], 1):
        role_data = {
            "user_id": user_id,
            "role_name": role,
            "role_name_normalized": role.lower().strip(),
            "priority": i
        }
        url = f"{SUPABASE_REST_URL}/user_preferred_roles"
        response = requests.post(url, headers=HEADERS, json=role_data, timeout=10)
        if response.status_code in [200, 201]:
            inserted.append(role)
    
    return {"inserted": inserted, "count": len(inserted)}


def save_user_api_key(user_id: str, api_key: str) -> dict:
    """Save user's Gemini API key."""
    # For simplicity, we'll store a hash and prefix
    # In production, encrypt the key properly
    import hashlib
    
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_prefix = api_key[:8] + "..." if len(api_key) > 8 else api_key
    
    # Check if exists
    check_url = f"{SUPABASE_REST_URL}/user_api_keys?user_id=eq.{user_id}&provider=eq.google_ai_studio"
    check_resp = requests.get(check_url, headers=HEADERS, timeout=10)
    
    key_data = {
        "user_id": user_id,
        "provider": "google_ai_studio",
        "api_key_hash": key_hash,
        "api_key_encrypted": api_key,  # In production, encrypt this!
        "api_key_prefix": key_prefix,
        "is_active": True
    }
    
    if check_resp.status_code == 200 and check_resp.json():
        # Update existing
        key_id = check_resp.json()[0]["id"]
        update_url = f"{SUPABASE_REST_URL}/user_api_keys?id=eq.{key_id}"
        requests.patch(update_url, headers=HEADERS, json=key_data, timeout=10)
        return {"status": "updated", "prefix": key_prefix}
    else:
        # Insert new
        url = f"{SUPABASE_REST_URL}/user_api_keys"
        requests.post(url, headers=HEADERS, json=key_data, timeout=10)
        return {"status": "created", "prefix": key_prefix}


def check_if_analysis_needed(user_id: str) -> bool:
    """
    Check if user needs analysis based on last activity.
    Returns True if:
    1. No previous analysis
    2. Resume uploaded AFTER last analysis
    3. GitHub synced AFTER last analysis
    """
    try:
        # 1. Get last analysis time
        url = f"{SUPABASE_REST_URL}/skill_gap_analyses?user_id=eq.{user_id}&select=analyzed_at&order=analyzed_at.desc&limit=1"
        resp = requests.get(url, headers=HEADERS, timeout=5)
        last_analysis = None
        if resp.status_code == 200 and resp.json():
            last_analysis = resp.json()[0]['analyzed_at']
        
        if not last_analysis:
            return True # Never analyzed

        # Convert to datetime (if string)
        # Handle formats efficiently
        if isinstance(last_analysis, str):
            last_analysis_dt = datetime.fromisoformat(last_analysis.replace('Z', '+00:00'))
        else:
            return True

        # 2. Get Profile (Resume upload)
        profile_url = f"{SUPABASE_REST_URL}/profiles?id=eq.{user_id}&select=resume_uploaded_at"
        p_resp = requests.get(profile_url, headers=HEADERS, timeout=5)
        if p_resp.status_code == 200 and p_resp.json():
            resume_uploaded = p_resp.json()[0].get('resume_uploaded_at')
            if resume_uploaded:
                resume_dt = datetime.fromisoformat(resume_uploaded.replace('Z', '+00:00'))
                if resume_dt > last_analysis_dt:
                    print(f"User {user_id}: New resume detected ({resume_dt}) > Last Analysis ({last_analysis_dt})")
                    return True

        # 3. Get GitHub Connection (Last Sync)
        gh_url = f"{SUPABASE_REST_URL}/github_connections?user_id=eq.{user_id}&select=last_sync_at"
        gh_resp = requests.get(gh_url, headers=HEADERS, timeout=5)
        if gh_resp.status_code == 200 and gh_resp.json():
            last_sync = gh_resp.json()[0].get('last_sync_at')
            if last_sync:
                sync_dt = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                if sync_dt > last_analysis_dt:
                    print(f"User {user_id}: New GitHub sync detected ({sync_dt}) > Last Analysis ({last_analysis_dt})")
                    return True
        
        return False
    except Exception as e:
        print(f"Error checking analysis need for {user_id}: {e}")
        return True # Fail safe: run it
