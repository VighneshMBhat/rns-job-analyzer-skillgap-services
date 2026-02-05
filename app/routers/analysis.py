"""
Analysis Router - Main endpoints for skill gap analysis
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.auth import get_current_user_id
from app.services.data_service import (
    get_user_profile,
    get_user_preferred_roles,
    get_user_skills,
    get_skill_trends,
    get_recent_jobs,
    get_recent_discussions,
    store_analysis_result,
    store_report_record,
    set_preferred_roles,
    save_user_api_key
)
from app.services.gemini_service import analyze_skill_gap
from app.services.pdf_service import generate_pdf_report, upload_to_s3, upload_to_supabase_storage
from datetime import datetime, timezone
import uuid

router = APIRouter()


class AnalysisRequest(BaseModel):
    preferred_roles: Optional[list[str]] = None  # If not provided, use saved roles


class SetRolesRequest(BaseModel):
    roles: list[str]  # Max 3 roles


class ApiKeyRequest(BaseModel):
    api_key: str


@router.post("/generate")
def generate_analysis(
    request: AnalysisRequest = None,
    user_id: str = Depends(get_current_user_id)
):
    """
    Generate a comprehensive skill gap analysis for the authenticated user.
    This is the main endpoint called by frontend button click.
    """
    try:
        # 1. Get user profile
        profile = get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        user_name = profile.get("full_name", "User")
        user_email = profile.get("email", "")
        
        # 2. Get preferred roles (from request or database)
        if request and request.preferred_roles:
            preferred_roles = request.preferred_roles[:3]
            # Save the roles for future use
            set_preferred_roles(user_id, preferred_roles)
        else:
            preferred_roles = get_user_preferred_roles(user_id)
            if not preferred_roles:
                raise HTTPException(
                    status_code=400,
                    detail="No preferred roles set. Please set your target roles first."
                )
        
        # 3. Get user's skills (from resume and GitHub)
        user_skills = get_user_skills(user_id)
        if not user_skills:
            raise HTTPException(
                status_code=400,
                detail="No skills found. Please connect GitHub or upload resume first."
            )
        
        # 4. Get market data
        skill_trends = get_skill_trends(limit=30)
        recent_jobs = get_recent_jobs(limit=50)
        recent_discussions = get_recent_discussions(limit=30)
        
        # 5. Run Gemini analysis
        analysis = analyze_skill_gap(
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            preferred_roles=preferred_roles,
            user_skills=user_skills,
            market_trends=skill_trends,
            trending_skills=skill_trends,
            recent_discussions=recent_discussions
        )
        
        # 6. Store analysis result
        analysis_id = store_analysis_result(user_id, preferred_roles, analysis)
        
        # 7. Generate PDF report
        pdf_buffer = generate_pdf_report(
            user_name=user_name,
            user_email=user_email,
            preferred_roles=preferred_roles,
            analysis=analysis,
            user_skills=user_skills
        )
        
        # 8. Upload PDF to storage
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"skill_gap_report_{user_id}_{timestamp}.pdf"
        
        # Get PDF size before upload
        pdf_buffer.seek(0, 2)  # Seek to end
        pdf_size = pdf_buffer.tell()
        pdf_buffer.seek(0)  # Reset to beginning
        
        report_url = upload_to_supabase_storage(pdf_buffer, filename)
        
        # 9. Store report record
        report_id = store_report_record(
            user_id=user_id,
            analysis_id=analysis_id,
            report_filename=filename,
            report_url=report_url,
            report_size=pdf_size
        )
        
        return {
            "status": "success",
            "analysis_id": analysis_id,
            "report_id": report_id,
            "report_url": report_url,
            "summary": {
                "overall_fit_score": analysis.get("overall_fit_score", 0),
                "overall_gap_percentage": analysis.get("overall_gap_percentage", 0),
                "market_readiness": analysis.get("skill_assessment", {}).get("market_readiness_score", 0),
                "critical_missing_skills": len(analysis.get("critical_missing_skills", [])),
                "api_key_source": analysis.get("api_key_source", "system")
            },
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/latest")
def get_latest_analysis(user_id: str = Depends(get_current_user_id)):
    """Get the user's most recent skill gap analysis."""
    from app.services.data_service import SUPABASE_REST_URL, HEADERS
    import requests
    
    url = f"{SUPABASE_REST_URL}/skill_gap_analyses?user_id=eq.{user_id}&select=*&order=analyzed_at.desc&limit=1"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200 and response.json():
        return response.json()[0]
    
    raise HTTPException(status_code=404, detail="No analysis found")


@router.get("/history")
def get_analysis_history(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    """Get history of user's skill gap analyses."""
    from app.services.data_service import SUPABASE_REST_URL, HEADERS
    import requests
    
    url = f"{SUPABASE_REST_URL}/skill_gap_analyses?user_id=eq.{user_id}&select=id,target_job_title,gap_percentage,role_fit_score,analyzed_at&order=analyzed_at.desc&limit={limit}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return {"analyses": response.json()}
    
    return {"analyses": []}


@router.post("/roles")
def set_user_preferred_roles(
    request: SetRolesRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Set user's preferred job roles (max 3)."""
    if len(request.roles) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 roles allowed")
    
    result = set_preferred_roles(user_id, request.roles)
    return {"status": "success", "roles": result}


@router.get("/roles")
def get_user_roles(user_id: str = Depends(get_current_user_id)):
    """Get user's preferred job roles."""
    roles = get_user_preferred_roles(user_id)
    return {"roles": roles}


@router.post("/api-key")
def set_gemini_api_key(
    request: ApiKeyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Save user's own Gemini API key (BYOK policy).
    The key is stored encrypted in the database.
    """
    # Basic validation
    if not request.api_key or len(request.api_key) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key format")
    
    result = save_user_api_key(user_id, request.api_key)
    return {
        "status": "success",
        "message": f"API key {result['status']}",
        "key_prefix": result["prefix"]
    }


@router.get("/reports")
def get_user_reports(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    """Get user's generated reports."""
    from app.services.data_service import SUPABASE_REST_URL, HEADERS
    import requests
    
    url = f"{SUPABASE_REST_URL}/reports?user_id=eq.{user_id}&select=id,report_filename,report_url,generated_at,email_sent,email_sent_at&order=generated_at.desc&limit={limit}"
    response = requests.get(url, headers=HEADERS, timeout=10)
    
    if response.status_code == 200:
        return {"reports": response.json()}
    
    return {"reports": []}
