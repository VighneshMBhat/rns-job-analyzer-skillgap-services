"""
Gemini AI Service - Skill Gap Analysis using Gemini 2.5 Pro
Implements BYOK (Bring Your Own Key) policy
"""
import google.generativeai as genai
from app.core.config import settings
import requests
import json
from typing import Optional

SUPABASE_REST_URL = f"{settings.SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": settings.SUPABASE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_KEY}",
    "Content-Type": "application/json"
}


def get_user_gemini_key(user_id: str) -> Optional[str]:
    """
    Get user's own Gemini API key from database.
    Returns None if user hasn't set their key.
    """
    try:
        url = f"{SUPABASE_REST_URL}/user_api_keys?user_id=eq.{user_id}&provider=eq.google_ai_studio&is_active=eq.true&select=api_key_encrypted"
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200 and response.json():
            encrypted_key = response.json()[0].get("api_key_encrypted")
            # In production, decrypt the key here
            # For now, we'll store keys in plain text temporarily
            return encrypted_key
        return None
    except Exception as e:
        print(f"Error fetching user API key: {e}")
        return None


def get_api_key_for_user(user_id: str) -> tuple[str, str]:
    """
    Get API key for user following BYOK policy.
    Returns (api_key, source) where source is 'user' or 'system'
    """
    # First try user's own key
    user_key = get_user_gemini_key(user_id)
    if user_key:
        return user_key, "user"
    
    # Fallback to system key
    if settings.GEMINI_API_KEY:
        return settings.GEMINI_API_KEY, "system"
    
    raise ValueError("No API key available. Please add your Gemini API key in settings.")


def analyze_skill_gap(
    user_id: str,
    user_name: str,
    user_email: str,
    preferred_roles: list[str],
    user_skills: list[dict],
    market_trends: list[dict],
    trending_skills: list[dict],
    recent_discussions: list[dict]
) -> dict:
    """
    Use Gemini 2.5 Pro to perform deep skill gap analysis.
    Returns comprehensive analysis with recommendations.
    """
    
    # Get API key (BYOK policy)
    api_key, key_source = get_api_key_for_user(user_id)
    
    # Configure Gemini
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    # Prepare the analysis prompt
    prompt = f"""You are an expert career advisor and technical skills analyst. Analyze the following data and provide a comprehensive skill gap analysis report.

## User Profile
- Name: {user_name}
- Email: {user_email}
- Target Roles: {', '.join(preferred_roles)}

## User's Current Skills (from Resume & GitHub Projects)
{json.dumps(user_skills, indent=2)}

## Current Market Trends (from Job Listings)
Top skills demanded in job postings:
{json.dumps(market_trends[:20], indent=2)}

## Trending Skills in Tech Community (from Reddit Discussions)
{json.dumps(trending_skills[:15], indent=2)}

## Recent Industry Discussions
{json.dumps([{{
    'title': d.get('title', ''),
    'subreddit': d.get('subreddit', ''),
    'upvotes': d.get('upvotes', 0)
}} for d in recent_discussions[:10]], indent=2)}

---

## Your Task

Provide a detailed skill gap analysis report with the following sections:

### 1. EXECUTIVE SUMMARY
Write 3-4 sentences summarizing the user's current market position and key findings.

### 2. CURRENT MARKET TRENDS
Based on the job listings and discussions:
- What are the top 5 in-demand skills right now?
- What technologies are growing in popularity?
- What's the overall direction of the tech job market?
- Include specific statistics if available.

### 3. USER'S SKILL ASSESSMENT
Analyze the user's current skills:
- List their strong skills (well-aligned with market demand)
- List skills they have but need improvement
- Rate their overall market readiness (1-10 scale)

### 4. SKILL GAP ANALYSIS FOR TARGET ROLES
For each of the user's target roles ({', '.join(preferred_roles)}):
- List the top 10 required skills for that role
- Identify which skills the user already has (✅)
- Identify which skills are missing (❌)
- Calculate gap percentage for each role

### 5. CRITICAL MISSING SKILLS
List the most important skills the user lacks, prioritized by:
- Market demand
- Relevance to target roles
- Learning difficulty (easy/medium/hard)

### 6. PERSONALIZED RECOMMENDATIONS
Provide specific, actionable recommendations:
- **Immediate Actions** (next 30 days): 3-5 specific things to do
- **Short-term Goals** (1-3 months): Skills to learn, projects to build
- **Long-term Strategy** (3-6 months): Career positioning advice

### 7. LEARNING RESOURCES
For the top 3 missing skills, suggest:
- Free resources (YouTube, documentation)
- Paid courses (Udemy, Coursera)
- Certifications to consider
- Projects to build for portfolio

### 8. MARKET COMPETITIVENESS SCORE
Rate the user's competitiveness on a scale of 1-100 for each target role, with brief explanation.

### 9. KEY INSIGHTS
Provide 3-5 unique insights that might not be obvious, based on the data analysis.

---

Format the response as a structured JSON object with the following keys:
{{
    "executive_summary": "string",
    "market_trends": {{
        "top_skills": ["list of top 5 skills"],
        "growing_technologies": ["list"],
        "market_direction": "string",
        "key_statistics": ["list of stats"]
    }},
    "skill_assessment": {{
        "strong_skills": ["list"],
        "needs_improvement": ["list"],
        "market_readiness_score": number (1-10),
        "assessment_notes": "string"
    }},
    "gap_analysis": [
        {{
            "role": "role name",
            "required_skills": ["list of 10 skills"],
            "user_has": ["skills user has"],
            "user_missing": ["skills user is missing"],
            "gap_percentage": number
        }}
    ],
    "critical_missing_skills": [
        {{
            "skill": "name",
            "importance": "high/medium/low",
            "learning_difficulty": "easy/medium/hard",
            "reason": "why important"
        }}
    ],
    "recommendations": {{
        "immediate_actions": ["list of 3-5 actions"],
        "short_term_goals": ["list of goals"],
        "long_term_strategy": "string"
    }},
    "learning_resources": [
        {{
            "skill": "skill name",
            "free_resources": ["list"],
            "paid_courses": ["list"],
            "certifications": ["list"],
            "project_ideas": ["list"]
        }}
    ],
    "competitiveness_scores": [
        {{
            "role": "role name",
            "score": number (1-100),
            "explanation": "string"
        }}
    ],
    "key_insights": ["list of 3-5 insights"],
    "overall_gap_percentage": number,
    "overall_fit_score": number (1-100),
    "report_generated_at": "current timestamp"
}}

Be thorough, specific, and actionable. The user will use this to guide their career development.
"""
    
    try:
        # Generate analysis using Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8000,
                response_mime_type="application/json"
            )
        )
        
        # Parse the response
        analysis_text = response.text
        
        # Try to parse as JSON
        try:
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            # If not valid JSON, wrap in a structure
            analysis = {
                "raw_analysis": analysis_text,
                "parse_error": True
            }
        
        analysis["api_key_source"] = key_source
        analysis["model_used"] = settings.GEMINI_MODEL
        
        return analysis
        
    except Exception as e:
        error_msg = str(e)
        
        # Check if it's a quota error
        if "quota" in error_msg.lower() or "limit" in error_msg.lower():
            # If user's key hit limit, try system key
            if key_source == "user" and settings.GEMINI_API_KEY:
                print(f"User key quota exceeded, falling back to system key")
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Recursively try with system key
                return analyze_skill_gap(
                    user_id, user_name, user_email, preferred_roles,
                    user_skills, market_trends, trending_skills, recent_discussions
                )
        
        raise Exception(f"Gemini analysis failed: {error_msg}")
