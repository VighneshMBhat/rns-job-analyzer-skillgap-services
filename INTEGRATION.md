# Skill Gap Analysis Service - Frontend Integration Guide

## 🔗 Service Overview

This service provides **AI-powered skill gap analysis** using **Gemini 2.5 Pro**. It analyzes a user's skills (from GitHub and resume) against current market trends and generates professional PDF reports with personalized recommendations.

---

## 📡 Production API

| Property | Value |
|----------|-------|
| **Base URL** | `https://tku29qrthd.execute-api.us-east-1.amazonaws.com/Prod` |
| **Authentication** | JWT Bearer Token (from Supabase Auth) |
| **AI Model** | Gemini 2.5 Pro |

---

## 🔐 Authentication

All endpoints (except health check) require the user's JWT access token.

### Getting the Access Token

```typescript
// Option 1: From localStorage (after login)
const accessToken = localStorage.getItem('access_token');

// Option 2: From Supabase client
const { data: { session } } = await supabase.auth.getSession();
const accessToken = session?.access_token;
```

### Adding to Request Headers

```typescript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};
```

---

## 📋 Prerequisites Before Analysis

Before generating a skill gap analysis, the user **MUST** have:

| Requirement | How to Check | What to Do If Missing |
|-------------|--------------|----------------------|
| ✅ Preferred Roles (1-3) | GET `/api/analysis/roles` | Show role selector UI |
| ✅ Skills Data | Query `user_skills` table | Prompt to connect GitHub or upload resume |

### Checking Prerequisites

```typescript
async function checkPrerequisites(accessToken: string): Promise<{
  hasRoles: boolean;
  hasSkills: boolean;
  roles: string[];
  skillsCount: number;
}> {
  const API_URL = 'https://tku29qrthd.execute-api.us-east-1.amazonaws.com/Prod';
  const headers = {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  };

  // Check roles
  const rolesResp = await fetch(`${API_URL}/api/analysis/roles`, { headers });
  const rolesData = await rolesResp.json();
  const roles = rolesData.roles || [];

  // Check skills from Supabase
  const { data: skills } = await supabase
    .from('user_skills')
    .select('id')
    .eq('user_id', userId);

  return {
    hasRoles: roles.length > 0,
    hasSkills: (skills?.length || 0) > 0,
    roles,
    skillsCount: skills?.length || 0
  };
}
```

---

## 🎯 API Endpoints

### 1. Set Preferred Roles ⭐ (Required First)

Users must set 1-3 target job roles before analysis.

```http
POST /api/analysis/roles
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "roles": ["Backend Developer", "DevOps Engineer", "Cloud Architect"]
}
```

**Response:**
```json
{
    "status": "success",
    "roles": {
        "inserted": ["Backend Developer", "DevOps Engineer", "Cloud Architect"],
        "count": 3
    }
}
```

**TypeScript Example:**
```typescript
interface SetRolesResponse {
  status: string;
  roles: {
    inserted: string[];
    count: number;
  };
}

const setPreferredRoles = async (
  accessToken: string,
  roles: string[]
): Promise<SetRolesResponse> => {
  // Maximum 3 roles allowed
  const validRoles = roles.slice(0, 3);
  
  const response = await fetch(
    `${API_URL}/api/analysis/roles`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ roles: validRoles })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to set roles');
  }

  return response.json();
};
```

**Suggested Roles for UI Dropdown:**
```typescript
const SUGGESTED_ROLES = [
  'Backend Developer',
  'Frontend Developer',
  'Full Stack Developer',
  'DevOps Engineer',
  'Data Scientist',
  'Data Engineer',
  'Machine Learning Engineer',
  'AI Engineer',
  'Cloud Architect',
  'Solutions Architect',
  'Mobile Developer',
  'iOS Developer',
  'Android Developer',
  'Site Reliability Engineer',
  'Security Engineer',
  'QA Engineer',
  'Product Manager',
  'Technical Lead',
  'Software Architect'
];
```

---

### 2. Get Preferred Roles

```http
GET /api/analysis/roles
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "roles": ["Backend Developer", "DevOps Engineer", "Cloud Architect"]
}
```

---

### 3. Set Gemini API Key (BYOK - Optional)

Users can provide their own Gemini API key. If not set, the system key is used.

```http
POST /api/analysis/api-key
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "api_key": "AIzaSy..."
}
```

**Response:**
```json
{
    "status": "success",
    "message": "API key created",
    "key_prefix": "AIzaSy..."
}
```

**Instructions for User:**
> Get your free Gemini API key from: https://aistudio.google.com/app/apikey

---

### 4. Generate Skill Gap Analysis ⭐ (Main Action)

This is the **main action** triggered when user clicks the "Analyze" button.

```http
POST /api/analysis/generate
Authorization: Bearer <access_token>
Content-Type: application/json

{
    "preferred_roles": ["Backend Developer", "DevOps Engineer"]
}
```

> **Note:** If `preferred_roles` is not provided, it uses the saved roles from the database.

**Response:**
```json
{
    "status": "success",
    "analysis_id": "uuid-of-analysis",
    "report_id": "uuid-of-report",
    "report_url": "https://supabase.storage/reports/skill_gap_report_xxx.pdf",
    "summary": {
        "overall_fit_score": 75,
        "overall_gap_percentage": 25,
        "market_readiness": 7,
        "critical_missing_skills": 5,
        "api_key_source": "system"
    },
    "analysis": {
        // Full analysis object (see below)
    }
}
```

**TypeScript Example:**
```typescript
interface AnalysisSummary {
  overall_fit_score: number;      // 1-100
  overall_gap_percentage: number;  // 0-100
  market_readiness: number;        // 1-10
  critical_missing_skills: number;
  api_key_source: 'user' | 'system';
}

interface AnalysisResult {
  status: string;
  analysis_id: string;
  report_id: string;
  report_url: string;
  summary: AnalysisSummary;
  analysis: FullAnalysis;
}

const generateAnalysis = async (
  accessToken: string,
  preferredRoles?: string[]
): Promise<AnalysisResult> => {
  const response = await fetch(
    `${API_URL}/api/analysis/generate`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        preferred_roles: preferredRoles 
      })
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Analysis failed');
  }

  return response.json();
};
```

**⏱️ Important:** This call takes **1-2 minutes** because Gemini AI performs deep analysis. Show a loading indicator!

---

### 5. Get Latest Analysis

```http
GET /api/analysis/latest
Authorization: Bearer <access_token>
```

**Response:** Returns the most recent analysis object.

---

### 6. Get Analysis History

```http
GET /api/analysis/history?limit=10
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "analyses": [
        {
            "id": "uuid",
            "target_job_title": "Backend Developer, DevOps Engineer",
            "gap_percentage": 25,
            "role_fit_score": 75,
            "analyzed_at": "2026-02-05T06:00:00Z"
        }
    ]
}
```

---

### 7. Get Generated Reports

```http
GET /api/analysis/reports?limit=10
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "reports": [
        {
            "id": "uuid",
            "report_filename": "skill_gap_report_xxx.pdf",
            "report_url": "https://...",
            "generated_at": "2026-02-05T06:00:00Z",
            "email_sent": true,
            "email_sent_at": "2026-02-05T07:00:00Z"
        }
    ]
}
```

---

## 📊 Full Analysis Object Structure

```typescript
interface FullAnalysis {
  // Executive overview
  executive_summary: string;
  
  // Market trends section
  market_trends: {
    top_skills: string[];           // Top 5 in-demand skills
    growing_technologies: string[]; // Emerging technologies
    market_direction: string;       // Overall market narrative
    key_statistics: string[];       // Specific stats and numbers
  };
  
  // User's current skill assessment
  skill_assessment: {
    strong_skills: string[];        // Skills aligned with market
    needs_improvement: string[];    // Skills requiring work
    market_readiness_score: number; // 1-10 scale
    assessment_notes: string;       // Detailed assessment
  };
  
  // Gap analysis per target role
  gap_analysis: Array<{
    role: string;                   // Target role name
    required_skills: string[];      // Top 10 required skills
    user_has: string[];             // Skills user already has
    user_missing: string[];         // Skills user is missing
    gap_percentage: number;         // 0-100
  }>;
  
  // Priority skills to learn
  critical_missing_skills: Array<{
    skill: string;
    importance: 'high' | 'medium' | 'low';
    learning_difficulty: 'easy' | 'medium' | 'hard';
    reason: string;                 // Why it's important
  }>;
  
  // Action items
  recommendations: {
    immediate_actions: string[];    // Next 30 days
    short_term_goals: string[];     // 1-3 months
    long_term_strategy: string;     // 3-6 months plan
  };
  
  // Learning resources
  learning_resources: Array<{
    skill: string;
    free_resources: string[];       // YouTube, docs, etc.
    paid_courses: string[];         // Udemy, Coursera, etc.
    certifications: string[];       // AWS, Google, etc.
    project_ideas: string[];        // Portfolio projects
  }>;
  
  // Competitiveness per role
  competitiveness_scores: Array<{
    role: string;
    score: number;                  // 1-100
    explanation: string;
  }>;
  
  // Unique insights
  key_insights: string[];           // 3-5 non-obvious insights
  
  // Overall scores
  overall_gap_percentage: number;   // 0-100
  overall_fit_score: number;        // 1-100
  report_generated_at: string;      // ISO timestamp
}
```

---

## 🎨 UI Components to Build

### 1. Role Selector Component

```tsx
interface RoleSelectorProps {
  selectedRoles: string[];
  onRolesChange: (roles: string[]) => void;
  maxRoles?: number;
}

const RoleSelector: React.FC<RoleSelectorProps> = ({
  selectedRoles,
  onRolesChange,
  maxRoles = 3
}) => {
  const handleAddRole = (role: string) => {
    if (selectedRoles.length < maxRoles && !selectedRoles.includes(role)) {
      onRolesChange([...selectedRoles, role]);
    }
  };

  const handleRemoveRole = (role: string) => {
    onRolesChange(selectedRoles.filter(r => r !== role));
  };

  return (
    <div className="role-selector">
      <h3>Select Your Target Roles (Max {maxRoles})</h3>
      
      {/* Selected roles chips */}
      <div className="selected-roles">
        {selectedRoles.map(role => (
          <Chip key={role} onRemove={() => handleRemoveRole(role)}>
            {role}
          </Chip>
        ))}
      </div>
      
      {/* Role suggestions dropdown */}
      <Select
        placeholder="Add a role..."
        options={SUGGESTED_ROLES.filter(r => !selectedRoles.includes(r))}
        onChange={handleAddRole}
        disabled={selectedRoles.length >= maxRoles}
      />
    </div>
  );
};
```

### 2. Analyze Button with Loading State

```tsx
const AnalyzeButton: React.FC<{
  isLoading: boolean;
  disabled: boolean;
  onClick: () => void;
}> = ({ isLoading, disabled, onClick }) => {
  return (
    <Button
      onClick={onClick}
      disabled={disabled || isLoading}
      size="lg"
      variant="primary"
    >
      {isLoading ? (
        <>
          <Spinner size="sm" />
          <span>Analyzing... (1-2 min)</span>
        </>
      ) : (
        <>
          <SparklesIcon />
          <span>Analyze My Skills</span>
        </>
      )}
    </Button>
  );
};
```

### 3. Results Dashboard

```tsx
const AnalysisDashboard: React.FC<{ result: AnalysisResult }> = ({ result }) => {
  const { summary, analysis, report_url } = result;
  
  return (
    <div className="analysis-dashboard">
      {/* Score Cards */}
      <div className="score-cards">
        <ScoreCard
          title="Overall Fit Score"
          value={summary.overall_fit_score}
          max={100}
          color={summary.overall_fit_score >= 70 ? 'green' : 'orange'}
        />
        <ScoreCard
          title="Skill Gap"
          value={summary.overall_gap_percentage}
          max={100}
          suffix="%"
          color={summary.overall_gap_percentage <= 30 ? 'green' : 'red'}
          inverted
        />
        <ScoreCard
          title="Market Readiness"
          value={summary.market_readiness}
          max={10}
        />
      </div>
      
      {/* Executive Summary */}
      <Card title="Executive Summary">
        <p>{analysis.executive_summary}</p>
      </Card>
      
      {/* Market Trends */}
      <Card title="Current Market Trends">
        <h4>Top In-Demand Skills</h4>
        <SkillsList skills={analysis.market_trends.top_skills} />
        
        <h4>Growing Technologies</h4>
        <SkillsList skills={analysis.market_trends.growing_technologies} />
      </Card>
      
      {/* Gap Analysis per Role */}
      <Card title="Gap Analysis by Role">
        {analysis.gap_analysis.map(role => (
          <RoleGapCard key={role.role} data={role} />
        ))}
      </Card>
      
      {/* Critical Skills */}
      <Card title="Skills to Prioritize">
        <table>
          <thead>
            <tr>
              <th>Skill</th>
              <th>Importance</th>
              <th>Difficulty</th>
            </tr>
          </thead>
          <tbody>
            {analysis.critical_missing_skills.map(skill => (
              <tr key={skill.skill}>
                <td>{skill.skill}</td>
                <td><Badge variant={skill.importance}>{skill.importance}</Badge></td>
                <td>{skill.learning_difficulty}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      
      {/* Recommendations */}
      <Card title="Recommendations">
        <h4>🚀 Immediate Actions (30 days)</h4>
        <ul>
          {analysis.recommendations.immediate_actions.map((action, i) => (
            <li key={i}>{action}</li>
          ))}
        </ul>
        
        <h4>📅 Short-Term Goals (1-3 months)</h4>
        <ul>
          {analysis.recommendations.short_term_goals.map((goal, i) => (
            <li key={i}>{goal}</li>
          ))}
        </ul>
      </Card>
      
      {/* Download Report */}
      <Button onClick={() => window.open(report_url, '_blank')}>
        📄 Download PDF Report
      </Button>
    </div>
  );
};
```

---

## ⚠️ Error Handling

```typescript
const handleAnalyze = async () => {
  setIsLoading(true);
  setError(null);
  
  try {
    const result = await generateAnalysis(accessToken);
    setResult(result);
    toast.success('Analysis complete! View your results below.');
    
  } catch (error: any) {
    const message = error.message || 'Analysis failed';
    
    if (message.includes('No preferred roles')) {
      setError('Please select your target job roles first.');
      setShowRoleSelector(true);
      
    } else if (message.includes('No skills found')) {
      setError('No skills data found. Please connect GitHub or upload your resume first.');
      
    } else if (message.includes('quota') || message.includes('limit')) {
      setError('API limit reached. Please add your own Gemini API key in settings.');
      
    } else if (message.includes('token') || message.includes('401')) {
      setError('Session expired. Please log in again.');
      router.push('/login');
      
    } else {
      setError('Analysis failed. Please try again later.');
    }
    
    toast.error(message);
  } finally {
    setIsLoading(false);
  }
};
```

---

## 🔄 Complete User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER JOURNEY                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User logs in (Supabase Auth)                                │
│          ↓                                                       │
│  2. Check prerequisites:                                         │
│     - Has skills? (from user_skills table)                      │
│     - Has preferred roles? (GET /api/analysis/roles)            │
│          ↓                                                       │
│  3. If no skills → Prompt to:                                   │
│     - Connect GitHub (GitHub Service)                           │
│     - Upload Resume                                             │
│          ↓                                                       │
│  4. If no roles → Show role selector UI                         │
│     - User selects 1-3 target roles                             │
│     - POST /api/analysis/roles                                  │
│          ↓                                                       │
│  5. User clicks "Analyze My Skills" button                      │
│     - POST /api/analysis/generate                               │
│     - Show loading (1-2 minutes)                                │
│          ↓                                                       │
│  6. Display results dashboard                                   │
│     - Overall scores                                            │
│     - Market trends                                             │
│     - Gap analysis per role                                     │
│     - Recommendations                                           │
│          ↓                                                       │
│  7. User can download PDF report                                │
│     - Open report_url in new tab                                │
│          ↓                                                       │
│  8. Weekly: User receives email with updated report             │
│     (handled by Reports & Notifications Service)                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Database Tables

### Tables to Query from Frontend

| Table | Purpose | Query Example |
|-------|---------|---------------|
| `user_skills` | User's extracted skills | `SELECT * FROM user_skills WHERE user_id = ?` |
| `user_preferred_roles` | Target job roles | Via API: `/api/analysis/roles` |
| `skill_gap_analyses` | Past analysis results | Via API: `/api/analysis/history` |
| `reports` | Generated PDF reports | Via API: `/api/analysis/reports` |
| `skill_trends` | Market trend data (read-only) | `SELECT * FROM skill_trends ORDER BY job_mention_count DESC LIMIT 20` |

### Example Supabase Query for Skills

```typescript
const getUserSkills = async (userId: string) => {
  const { data, error } = await supabase
    .from('user_skills')
    .select('skill_name, source, proficiency_level, confidence_score')
    .eq('user_id', userId)
    .order('confidence_score', { ascending: false });
  
  return data || [];
};
```

---

## 🔧 Settings Page UI

### Gemini API Key Input (BYOK)

```tsx
const GeminiApiKeySettings: React.FC = () => {
  const [apiKey, setApiKey] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [savedPrefix, setSavedPrefix] = useState<string | null>(null);
  
  const handleSave = async () => {
    setIsSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/analysis/api-key`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ api_key: apiKey })
      });
      
      const data = await response.json();
      setSavedPrefix(data.key_prefix);
      setApiKey('');
      toast.success('API key saved successfully!');
    } catch (error) {
      toast.error('Failed to save API key');
    } finally {
      setIsSaving(false);
    }
  };
  
  return (
    <Card title="Gemini API Key (Optional)">
      <p>
        Provide your own Gemini API key for unlimited analysis.
        <a href="https://aistudio.google.com/app/apikey" target="_blank">
          Get one free from Google AI Studio
        </a>
      </p>
      
      {savedPrefix && (
        <div className="saved-key">
          Current key: <code>{savedPrefix}</code>
        </div>
      )}
      
      <Input
        type="password"
        placeholder="AIzaSy..."
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
      />
      
      <Button onClick={handleSave} disabled={isSaving || !apiKey}>
        {isSaving ? 'Saving...' : 'Save API Key'}
      </Button>
    </Card>
  );
};
```

---

## 📧 Weekly Reports (Automatic)

The service automatically runs every **Sunday at 04:00 UTC** and:

1. Generates skill gap analysis for ALL users with skills and roles set
2. Creates PDF reports
3. Stores in `reports` table with `email_sent = false`

The **Reports & Notifications Service** (your friend's service) should:

1. Query: `SELECT * FROM reports WHERE email_sent = false`
2. Download PDF from `report_url`
3. Send email to user
4. Update: `UPDATE reports SET email_sent = true, email_sent_at = NOW()`

---

## 🧪 Testing the API

### Test with cURL

```bash
# 1. Get access token (login first via frontend, then grab from localStorage)
ACCESS_TOKEN="your_jwt_token"

# 2. Set preferred roles
curl -X POST "https://tku29qrthd.execute-api.us-east-1.amazonaws.com/Prod/api/analysis/roles" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["Backend Developer", "DevOps Engineer"]}'

# 3. Generate analysis
curl -X POST "https://tku29qrthd.execute-api.us-east-1.amazonaws.com/Prod/api/analysis/generate" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 📞 Contact & Support

| Resource | Link |
|----------|------|
| API Base URL | `https://tku29qrthd.execute-api.us-east-1.amazonaws.com/Prod` |
| GitHub Repository | https://github.com/VighneshMBhat/rns-job-analyzer-skillgap-services |
| Supabase Dashboard | https://supabase.com/dashboard/project/rokptxcawrmhqcmrsjca |

---

## ✅ Quick Checklist

- [ ] Add `NEXT_PUBLIC_SKILLGAP_SERVICE_URL` to frontend `.env`
- [ ] Implement role selector UI
- [ ] Implement analyze button with loading state
- [ ] Implement results dashboard
- [ ] Add BYOK settings page
- [ ] Handle all error states
- [ ] Test with real JWT token
