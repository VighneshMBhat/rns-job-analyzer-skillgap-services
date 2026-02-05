# Skill Gap Analysis Service - Frontend Integration Guide

## 🔗 Service Overview

This service provides AI-powered skill gap analysis using **Gemini 2.5 Pro**.

**Production API URL**: *(Will be provided after AWS deployment)*

---

## 🔐 Authentication

All endpoints require the user's JWT access token from Supabase Auth.

```typescript
const accessToken = localStorage.getItem('access_token');
// OR from Supabase client
const { data: { session } } = await supabase.auth.getSession();
const accessToken = session?.access_token;
```

**Header format:**
```
Authorization: Bearer <access_token>
```

---

## 📡 API Endpoints

### 1. Set User's Preferred Roles (Required First)

Before generating analysis, user must set their target job roles.

```typescript
const setPreferredRoles = async (roles: string[]) => {
  const response = await fetch(`${API_URL}/api/analysis/roles`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ roles: roles.slice(0, 3) }) // Max 3 roles
  });
  return response.json();
};

// Example
await setPreferredRoles(['Backend Developer', 'DevOps Engineer', 'Cloud Architect']);
```

---

### 2. Set User's Gemini API Key (Optional - BYOK)

Users can provide their own Gemini API key to avoid hitting system limits.

```typescript
const setGeminiApiKey = async (apiKey: string) => {
  const response = await fetch(`${API_URL}/api/analysis/api-key`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ api_key: apiKey })
  });
  return response.json();
};
```

**Get Gemini API Key from:** https://aistudio.google.com/app/apikey

---

### 3. Generate Skill Gap Analysis (Main Action)

This is the main button click action.

```typescript
interface AnalysisResult {
  status: string;
  analysis_id: string;
  report_id: string;
  report_url: string;
  summary: {
    overall_fit_score: number;
    overall_gap_percentage: number;
    market_readiness: number;
    critical_missing_skills: number;
    api_key_source: 'user' | 'system';
  };
  analysis: FullAnalysis;
}

const generateAnalysis = async (preferredRoles?: string[]): Promise<AnalysisResult> => {
  const response = await fetch(`${API_URL}/api/analysis/generate`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ preferred_roles: preferredRoles })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Analysis failed');
  }
  
  return response.json();
};
```

**Usage in React:**
```tsx
const [isLoading, setIsLoading] = useState(false);
const [result, setResult] = useState<AnalysisResult | null>(null);

const handleAnalyze = async () => {
  setIsLoading(true);
  try {
    const result = await generateAnalysis(['Backend Developer', 'DevOps Engineer']);
    setResult(result);
    
    // Show success message
    toast.success('Analysis complete! Download your report.');
    
    // Open PDF in new tab
    if (result.report_url) {
      window.open(result.report_url, '_blank');
    }
  } catch (error) {
    toast.error(error.message);
  } finally {
    setIsLoading(false);
  }
};
```

---

### 4. Get Latest Analysis

```typescript
const getLatestAnalysis = async () => {
  const response = await fetch(`${API_URL}/api/analysis/latest`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  return response.json();
};
```

---

### 5. Get Analysis History

```typescript
const getAnalysisHistory = async (limit: number = 10) => {
  const response = await fetch(`${API_URL}/api/analysis/history?limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  return response.json();
};
```

---

### 6. Get Generated Reports

```typescript
const getReports = async (limit: number = 10) => {
  const response = await fetch(`${API_URL}/api/analysis/reports?limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  return response.json();
};
```

---

## 📊 Response Data Structure

### Full Analysis Object

```typescript
interface FullAnalysis {
  executive_summary: string;
  
  market_trends: {
    top_skills: string[];
    growing_technologies: string[];
    market_direction: string;
    key_statistics: string[];
  };
  
  skill_assessment: {
    strong_skills: string[];
    needs_improvement: string[];
    market_readiness_score: number; // 1-10
    assessment_notes: string;
  };
  
  gap_analysis: Array<{
    role: string;
    required_skills: string[];
    user_has: string[];
    user_missing: string[];
    gap_percentage: number;
  }>;
  
  critical_missing_skills: Array<{
    skill: string;
    importance: 'high' | 'medium' | 'low';
    learning_difficulty: 'easy' | 'medium' | 'hard';
    reason: string;
  }>;
  
  recommendations: {
    immediate_actions: string[];
    short_term_goals: string[];
    long_term_strategy: string;
  };
  
  learning_resources: Array<{
    skill: string;
    free_resources: string[];
    paid_courses: string[];
    certifications: string[];
    project_ideas: string[];
  }>;
  
  competitiveness_scores: Array<{
    role: string;
    score: number; // 1-100
    explanation: string;
  }>;
  
  key_insights: string[];
  overall_gap_percentage: number;
  overall_fit_score: number; // 1-100
  report_generated_at: string;
}
```

---

## 🎨 UI Components to Build

### 1. Preferred Roles Selector
```tsx
<RolesSelector
  maxRoles={3}
  selectedRoles={preferredRoles}
  onRolesChange={setPreferredRoles}
  suggestedRoles={[
    'Backend Developer',
    'Frontend Developer',
    'Full Stack Developer',
    'DevOps Engineer',
    'Data Scientist',
    'Machine Learning Engineer',
    'Cloud Architect',
    'Mobile Developer'
  ]}
/>
```

### 2. Analyze Button
```tsx
<Button
  onClick={handleAnalyze}
  disabled={isLoading || preferredRoles.length === 0}
  loading={isLoading}
>
  {isLoading ? 'Analyzing... (may take 1-2 minutes)' : 'Analyze My Skills'}
</Button>
```

### 3. Results Dashboard
```tsx
<AnalysisDashboard
  fitScore={result.summary.overall_fit_score}
  gapPercentage={result.summary.overall_gap_percentage}
  marketReadiness={result.summary.market_readiness}
  criticalSkillsCount={result.summary.critical_missing_skills}
/>
```

### 4. Download Report Button
```tsx
<Button onClick={() => window.open(result.report_url, '_blank')}>
  📄 Download PDF Report
</Button>
```

---

## ⚠️ Error Handling

```typescript
const handleAnalyze = async () => {
  try {
    const result = await generateAnalysis();
    // Success
  } catch (error: any) {
    if (error.message.includes('No preferred roles')) {
      toast.error('Please set your target roles first');
    } else if (error.message.includes('No skills found')) {
      toast.error('Please connect GitHub or upload resume first');
    } else if (error.message.includes('quota') || error.message.includes('limit')) {
      toast.error('API limit reached. Please add your own Gemini API key.');
    } else {
      toast.error('Analysis failed. Please try again.');
    }
  }
};
```

---

## 📋 Prerequisites Before Analysis

User must have:
1. ✅ **Preferred Roles Set** (1-3 job roles)
2. ✅ **Skills Data** (either from GitHub connection OR resume upload)

Show these requirements on the UI:
```tsx
{!hasPreferredRoles && (
  <Alert>Please select your target job roles first</Alert>
)}
{!hasSkills && (
  <Alert>Please connect GitHub or upload your resume first</Alert>
)}
```

---

## 🔄 Typical User Flow

```
1. User goes to Dashboard
2. User connects GitHub (optional)
3. User uploads Resume (optional)
4. User sets 3 preferred job roles
5. User clicks "Analyze My Skills"
6. Loading spinner for 1-2 minutes (AI processing)
7. Results display on dashboard
8. User can download PDF report
9. Report is automatically emailed weekly
```

---

## 📞 Contact

For API issues, contact the backend team.

**GitHub Repository**: *(To be added)*
