# Skill Gap Analysis Service

AI-powered skill gap analysis using **Gemini 2.5 Pro**.

## 🌟 Features

- **Deep Skill Gap Analysis**: Uses Gemini 2.5 Pro to analyze user skills against market trends
- **Professional PDF Reports**: Generates detailed reports with charts and recommendations
- **BYOK Policy**: Users can bring their own Gemini API key
- **Weekly CRON Job**: Automatically generates reports for all users
- **JWT Authentication**: Secure endpoints using Supabase Auth tokens

## 📡 API Endpoints

### Authentication Required Endpoints

All endpoints require `Authorization: Bearer <access_token>` header.

#### Generate Analysis
```http
POST /api/analysis/generate
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "preferred_roles": ["Backend Developer", "DevOps Engineer", "Cloud Architect"]
}
```

**Response:**
```json
{
    "status": "success",
    "analysis_id": "uuid",
    "report_id": "uuid",
    "report_url": "https://...",
    "summary": {
        "overall_fit_score": 75,
        "overall_gap_percentage": 25,
        "market_readiness": 7,
        "critical_missing_skills": 5
    },
    "analysis": { ... }
}
```

#### Set Preferred Roles
```http
POST /api/analysis/roles
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "roles": ["Backend Developer", "DevOps Engineer", "Cloud Architect"]
}
```

#### Get Preferred Roles
```http
GET /api/analysis/roles
Authorization: Bearer <access_token>
```

#### Set Gemini API Key (BYOK)
```http
POST /api/analysis/api-key
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "api_key": "your-gemini-api-key"
}
```

#### Get Analysis History
```http
GET /api/analysis/history?limit=10
Authorization: Bearer <access_token>
```

#### Get Latest Analysis
```http
GET /api/analysis/latest
Authorization: Bearer <access_token>
```

#### Get Reports
```http
GET /api/analysis/reports?limit=10
Authorization: Bearer <access_token>
```

### CRON Endpoints (No Auth - Called by EventBridge)

#### Run Weekly Analysis
```http
POST /api/cron/run
```

#### Get CRON Status
```http
GET /api/cron/status
```

## 🔧 Local Development

1. **Create virtual environment:**
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Create .env file:**
```bash
copy .env.example .env
# Edit .env with your values
```

4. **Run locally:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

5. **Test:**
```bash
curl http://localhost:8003/
```

## 🚀 AWS Deployment

1. **Build:**
```bash
sam build
```

2. **Deploy:**
```bash
sam deploy --stack-name skillgap-service ^
  --resolve-s3 ^
  --capabilities CAPABILITY_IAM ^
  --region us-east-1 ^
  --profile rns-auth ^
  --parameter-overrides ^
    SupabaseUrl="https://rokptxcawrmhqcmrsjca.supabase.co" ^
    SupabaseKey="your_key" ^
    SupabaseServiceRoleKey="your_service_role_key" ^
    GeminiApiKey="your_gemini_key"
```

## 📊 Data Flow

```
┌───────────────────────────────────────────────────────────────────┐
│                      SKILL GAP ANALYSIS SERVICE                    │
│                                                                    │
│   1. User clicks "Analyze" button (or weekly CRON triggers)       │
│   2. Fetch user's skills (from GitHub + Resume)                   │
│   3. Fetch market trends (from fetched_jobs + skill_trends)       │
│   4. Fetch discussions (from fetched_discussions)                 │
│   5. Send all data to Gemini 2.5 Pro for deep analysis           │
│   6. Generate professional PDF report                             │
│   7. Upload PDF to S3/Supabase Storage                           │
│   8. Store analysis results in skill_gap_analyses table          │
│   9. Store report record in reports table                        │
│  10. Return results + report URL to frontend                      │
└───────────────────────────────────────────────────────────────────┘
```

## 🗄️ Database Tables Used

| Table | Purpose |
|-------|---------|
| `profiles` | User information |
| `user_preferred_roles` | User's target job roles (max 3) |
| `user_skills` | Skills extracted from GitHub + Resume |
| `user_api_keys` | User's own Gemini API keys (BYOK) |
| `skill_trends` | Market trend data (from trend service) |
| `fetched_jobs` | Job listings (from trend service) |
| `fetched_discussions` | Reddit discussions (from trend service) |
| `skill_gap_analyses` | Analysis results |
| `reports` | Generated PDF report records |

## 🔒 Security

- **JWT Authentication**: All user endpoints require valid Supabase access token
- **BYOK Policy**: Users can use their own Gemini API key
- **API Key Storage**: Keys are stored with hash for verification
- **RLS**: Row Level Security on all user data tables

## 📅 CRON Schedule

| Schedule | Time | What It Does |
|----------|------|--------------|
| Weekly | Sunday 04:00 UTC | Generate skill gap analysis for all eligible users |

## 📞 Integration with Reports Service

The generated PDF reports are stored in the `reports` table with the following fields:
- `user_id`: Owner of the report
- `report_url`: URL to download the PDF
- `email_sent`: Boolean (set by Reports & Notifications service)
- `email_sent_at`: Timestamp when email was sent

The Reports & Notifications service reads this table and emails reports to users.
