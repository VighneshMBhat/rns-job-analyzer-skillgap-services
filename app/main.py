"""
Skill Gap Analysis Service - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from app.routers import analysis, cron

app = FastAPI(
    title="Skill Gap Analysis Service",
    description="AI-powered skill gap analysis using Gemini 2.5 Pro",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(cron.router, prefix="/api/cron", tags=["CRON"])


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "service": "Skill Gap Analysis Service",
        "version": "1.0.0",
        "status": "running",
        "ai_model": "Gemini 2.5 Pro",
        "endpoints": {
            "analysis": "/api/analysis",
            "cron": "/api/cron"
        }
    }


@app.get("/api/health")
def api_health():
    """API health check."""
    return {"status": "healthy"}


# AWS Lambda handler
handler = Mangum(app)
