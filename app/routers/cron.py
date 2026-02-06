"""
CRON Router - Weekly scheduled skill gap analysis for all users
"""
from fastapi import APIRouter, HTTPException
from app.services.data_service import (
    get_all_users_for_cron,
    get_user_profile,
    get_user_preferred_roles,
    get_user_skills,
    get_skill_trends,
    get_recent_discussions,
    store_analysis_result,
    store_report_record,
    check_if_analysis_needed
)
from app.services.gemini_service import analyze_skill_gap
from app.services.pdf_service import generate_pdf_report, upload_to_supabase_storage
from datetime import datetime, timezone
import traceback

router = APIRouter()


@router.post("/run")
def run_weekly_analysis():
    """
    CRON endpoint - Run weekly skill gap analysis for ALL users.
    This is triggered by AWS EventBridge scheduler.
    """
    results = []
    errors = []
    
    # Get all users who should receive weekly reports
    users = get_all_users_for_cron()
    
    if not users:
        return {
            "status": "completed",
            "message": "No users to process",
            "processed": 0
        }
    
    # Get shared market data (same for all users)
    skill_trends = get_skill_trends(limit=30)
    recent_discussions = get_recent_discussions(limit=30)
    
    for user in users:
        user_id = user.get("id")
        user_name = user.get("full_name", "User")
        user_email = user.get("email", "")
        
        try:
            # Check if analysis is needed (Smart Cron)
            if not check_if_analysis_needed(user_id):
                results.append({
                    "user_id": user_id,
                    "status": "skipped",
                    "reason": "No new data (Resume/GitHub unchanged)"
                })
                continue

            # Get user-specific data
            preferred_roles = get_user_preferred_roles(user_id)
            if not preferred_roles:
                results.append({
                    "user_id": user_id,
                    "status": "skipped",
                    "reason": "No preferred roles set"
                })
                continue
            
            user_skills = get_user_skills(user_id)
            if not user_skills:
                results.append({
                    "user_id": user_id,
                    "status": "skipped",
                    "reason": "No skills found"
                })
                continue
            
            # Run analysis
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
            
            # Store analysis
            analysis_id = store_analysis_result(user_id, preferred_roles, analysis)
            
            # Generate PDF
            pdf_buffer = generate_pdf_report(
                user_name=user_name,
                user_email=user_email,
                preferred_roles=preferred_roles,
                analysis=analysis,
                user_skills=user_skills
            )
            
            # Upload PDF
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"skill_gap_report_{user_id}_{timestamp}.pdf"
            
            pdf_buffer.seek(0, 2)
            pdf_size = pdf_buffer.tell()
            pdf_buffer.seek(0)
            
            report_url = upload_to_supabase_storage(pdf_buffer, filename)
            
            # Store report record
            report_id = store_report_record(
                user_id=user_id,
                analysis_id=analysis_id,
                report_filename=filename,
                report_url=report_url,
                report_size=pdf_size
            )
            
            results.append({
                "user_id": user_id,
                "status": "success",
                "analysis_id": analysis_id,
                "report_id": report_id,
                "overall_fit_score": analysis.get("overall_fit_score", 0)
            })
            
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"Error processing user {user_id}: {error_msg}")
            traceback.print_exc()
            errors.append({
                "user_id": user_id,
                "error": error_msg
            })
    
    return {
        "status": "completed",
        "processed": len(results),
        "skipped": len([r for r in results if r.get("status") == "skipped"]),
        "errors": len(errors),
        "results": results,
        "error_details": errors[:5] if errors else None
    }


@router.get("/status")
def get_cron_status():
    """Get status of the CRON job configuration."""
    users = get_all_users_for_cron()
    trends = get_skill_trends(limit=5)
    
    return {
        "status": "ready",
        "eligible_users": len(users),
        "has_trend_data": len(trends) > 0,
        "schedule": "Weekly (Sundays 04:00 UTC)",
        "last_run": "Check CloudWatch logs for details"
    }
