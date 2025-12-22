# 🔍 REACT MIGRATION ARCHITECTURE AUDIT
**Date:** December 22, 2025  
**Purpose:** Pre-migration assessment for Streamlit → React.js transition  
**Status:** ⚠️ MEDIUM DIFFICULTY - Significant refactoring required

---

## 📊 EXECUTIVE SUMMARY

### Migration Difficulty: **MEDIUM** ⚠️

**Good News:**
- ✅ Core business logic (agent.py, assessment_engine.py) is **mostly decoupled** from Streamlit
- ✅ Database layer (SQLAlchemy) is **framework-agnostic**
- ✅ Clear data models already exist (StudentSession, ChatLog, ExamResult)

**Challenges:**
- ⚠️ State management is **heavily coupled** to `st.session_state` in UI pages
- ⚠️ `ScenarioManager` uses **in-memory global dict** (`_STUDENT_STATES`) instead of DB
- ⚠️ No REST API layer exists - `main.py` is just a Streamlit redirect

---

## 1️⃣ LOGIC COUPLING ANALYSIS

### ✅ **CLEAN LAYERS** (API-Ready)

#### **app/agent.py** - `DentalEducationAgent`
```python
Status: ✅ FULLY DECOUPLED
Streamlit Dependencies: NONE

Public Methods:
- interpret_action(action, state) -> Dict
- process_student_input(student_id, raw_action, case_id) -> Dict

Return Type: Pure Python dicts (JSON-serializable)
```

**Analysis:** This is your **golden layer**. The agent:
- Takes plain Python inputs (strings, dicts)
- Returns structured JSON dictionaries
- Has NO `st.*` calls anywhere in the code
- Can be called directly from FastAPI without modification

#### **app/assessment_engine.py** - `AssessmentEngine`
```python
Status: ✅ FULLY DECOUPLED
Streamlit Dependencies: NONE

Public Methods:
- evaluate_action(case_id, interpretation) -> Dict

Data Source: JSON file (data/scoring_rules.json)
```

**Analysis:** Pure rule engine, completely framework-agnostic.

#### **app/analytics_engine.py** - `analyze_performance()`
```python
Status: ✅ FULLY DECOUPLED
Streamlit Dependencies: NONE

Input: pandas DataFrame
Output: Dict with performance metrics
```

**Analysis:** Stateless analytics function, ready for API exposure.

#### **db/database.py** - SQLAlchemy Models
```python
Status: ✅ FULLY DECOUPLED
Streamlit Dependencies: NONE

Models:
- StudentSession
- ChatLog  
- ExamResult

Helper Functions:
- save_exam_result()
- get_user_stats()
- get_student_detailed_history()
```

**Analysis:** Database layer is production-ready. Already uses proper ORM patterns.

---

### ⚠️ **PROBLEMATIC LAYERS** (Need Refactoring)

#### **app/scenario_manager.py** - `ScenarioManager`
```python
Status: ⚠️ ARCHITECTURAL PROBLEM
Issue: Uses in-memory global dictionary for state

# Global in-memory store simulating a database
_STUDENT_STATES: Dict[str, Dict[str, Any]] = {}
```

**Problems:**
1. ❌ State is **not persisted** - lost on server restart
2. ❌ Not **thread-safe** for production API
3. ❌ Cannot scale horizontally (no shared state)
4. ❌ Duplicates data already in `StudentSession` table

**Solution:** Refactor to use `StudentSession` table instead of global dict.

#### **pages/*.py** - All UI Pages
```python
Status: ❌ HEAVILY COUPLED TO STREAMLIT
Dependencies: 48+ references to st.session_state

Key Files:
- pages/3_chat.py (35 st.session_state calls)
- pages/0_home.py (4 st.session_state calls)
- pages/1_login.py (6 st.session_state calls)
- pages/5_stats.py (1 st.session_state call)
```

**What's stored in `st.session_state`:**
```python
{
    "student_profile": {...},        # User auth data
    "is_logged_in": bool,           # Auth status
    "current_case_id": str,         # Active case
    "messages": [...],              # Chat history (UI only)
    "db_session_id": int,           # DB session reference
    "selected_model": str,          # Gemini model selection
    "case_completed": bool          # Case completion flag
}
```

**Analysis:** These values need to be managed by:
- **React state** (UI-specific: `messages`, `selected_model`)
- **API context** (auth: `is_logged_in`, `student_profile`)
- **Database** (persistent: `current_case_id`, `db_session_id`)

---

## 2️⃣ STATE MANAGEMENT AUDIT

### Current State Architecture

```
STREAMLIT WORLD:
┌─────────────────────────────────────┐
│     st.session_state (ephemeral)    │
│  ┌──────────┐    ┌───────────────┐  │
│  │ messages │    │ student_profile│  │
│  └──────────┘    └───────────────┘  │
│  ┌──────────┐    ┌───────────────┐  │
│  │ case_id  │    │ db_session_id │  │
│  └──────────┘    └───────────────┘  │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│ ScenarioManager._STUDENT_STATES     │
│       (in-memory global dict)       │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    SQLite Database (persistent)     │
│  StudentSession | ChatLog | ...     │
└─────────────────────────────────────┘
```

### Recommended React Architecture

```
REACT + FASTAPI WORLD:
┌─────────────────────────────────────┐
│   React State (client-side)         │
│  - messages (UI chat bubbles)       │
│  - isLoading, selectedModel, etc.   │
└─────────────────────────────────────┘
           ↓ HTTP Requests
┌─────────────────────────────────────┐
│        FastAPI Backend              │
│  - JWT auth (stateless)             │
│  - Request context only             │
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    PostgreSQL/SQLite Database       │
│  - StudentSession (case state)      │
│  - ChatLog (message history)        │
│  - User auth, profiles, etc.        │
└─────────────────────────────────────┘
```

---

### 🎯 **Clear Data Model for "Current State"**

**Yes!** The database already has a good model:

#### `StudentSession` Table
```python
class StudentSession(Base):
    id: int                    # Session identifier
    student_id: str           # Who is playing
    case_id: str              # Which case
    current_score: float      # Live score
    start_time: datetime      # When started
    chat_logs: [ChatLog]      # Message history (relationship)
```

**API Response Shape:**
```json
{
  "session_id": 42,
  "student_id": "2021001",
  "case_id": "olp_001",
  "current_score": 35.5,
  "case_info": {
    "name": "Oral Liken Planus",
    "difficulty": "Orta",
    "patient": {
      "age": 45,
      "chief_complaint": "Ağızda yanma"
    }
  },
  "revealed_findings": ["finding_001", "finding_002"],
  "messages": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "...", "metadata": {...}}
  ]
}
```

**Missing Piece:** `revealed_findings` is currently stored in `ScenarioManager` global dict.  
**Solution:** Add `state_json` column to `StudentSession`:

```python
class StudentSession(Base):
    # ... existing fields ...
    state_json = Column(JSON, nullable=True)  # Store revealed_findings, etc.
```

---

## 3️⃣ API READINESS ASSESSMENT

### Current `main.py`
```python
# Just a Streamlit redirect - NOT API-ready
import streamlit as st
st.switch_page("pages/0_home.py")
```

**Status:** ❌ Not usable as FastAPI entry point

### Required FastAPI Structure

```python
# NEW: app/api/main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat, auth, cases, analytics

app = FastAPI(title="Dental Tutor API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(cases.router, prefix="/api/cases", tags=["cases"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

---

## 🚨 BLOCKING ISSUES

### Critical Blockers

1. **ScenarioManager State Persistence**
   ```
   Problem: _STUDENT_STATES global dict will be empty on each API restart
   Impact: Students lose revealed_findings mid-session
   Solution: Migrate to StudentSession.state_json column
   ```

2. **Authentication System**
   ```
   Problem: st.session_state.is_logged_in won't work in stateless API
   Impact: No auth protection for endpoints
   Solution: Implement JWT token-based auth
   ```

3. **File Uploads (if any)**
   ```
   Problem: Streamlit file uploader returns different object than HTTP multipart
   Impact: Image/media handling needs rewrite
   Solution: Use FastAPI's UploadFile
   ```

### Non-Blocking Issues (Can be done incrementally)

- ℹ️ Sidebar component (frontend-specific, React will rebuild)
- ℹ️ CSS styling (Streamlit → Tailwind/MUI)
- ℹ️ Chart rendering (Streamlit charts → Chart.js/Recharts)

---

## 📋 FIRST STEP RECOMMENDATION

### 🎯 **Phase 1: Create Parallel API (Don't break Streamlit yet)**

**Week 1: Proof of Concept API**

```bash
# Create new folder structure
mkdir -p app/api/routers
touch app/api/__init__.py
touch app/api/main.py
touch app/api/routers/{auth,chat,cases}.py
```

**Priority Order:**

1. ✅ **Create `/api/chat/send` endpoint** (2-3 hours)
   - Reuse `DentalEducationAgent.process_student_input()`
   - Input: `{"student_id": "...", "message": "...", "case_id": "..."}`
   - Output: `{"response": "...", "score": 10, "metadata": {...}}`
   - **No Streamlit dependencies!**

2. ✅ **Fix ScenarioManager persistence** (3-4 hours)
   - Add `state_json` column to `StudentSession`
   - Refactor `get_state()` to read from DB instead of global dict
   - Refactor `update_state()` to write to DB

3. ✅ **Create `/api/auth/login` endpoint** (2 hours)
   - Simple JWT token generation
   - Validate against existing student records

4. ✅ **Create `/api/cases/{case_id}` endpoint** (1 hour)
   - Return case data from JSON files
   - No coupling issues here

**Test with cURL before building React:**
```bash
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"student_id": "2021001", "message": "Hastanın alerjisini kontrol ediyorum", "case_id": "olp_001"}'
```

---

### ⚡ **Quick Win: Minimal API Prototype**

Create this file to prove decoupling works:

**File:** `app/api/chat_prototype.py`
```python
"""
Proof of Concept: Chat API without Streamlit
Run: uvicorn app.api.chat_prototype:app --reload
"""
from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import DentalEducationAgent
import os

app = FastAPI()

class ChatRequest(BaseModel):
    student_id: str
    message: str
    case_id: str = "olp_001"

class ChatResponse(BaseModel):
    response: str
    score: float
    action: str

# Initialize agent (reuse existing code!)
agent = DentalEducationAgent(
    api_key=os.getenv("GEMINI_API_KEY"),
    model_name="models/gemini-2.5-flash-lite"
)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # ZERO Streamlit dependencies!
    result = agent.process_student_input(
        student_id=req.student_id,
        raw_action=req.message,
        case_id=req.case_id
    )
    
    return ChatResponse(
        response=result["final_feedback"],
        score=result["assessment"].get("score", 0),
        action=result["llm_interpretation"].get("interpreted_action", "")
    )

@app.get("/health")
def health():
    return {"status": "ok", "engine": "DentalEducationAgent"}
```

**Run this NOW to prove it works:**
```bash
pip install fastapi uvicorn
uvicorn app.api.chat_prototype:app --reload --port 8000
```

**Test:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","engine":"DentalEducationAgent"}

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"student_id":"test","message":"Alerjileri kontrol et","case_id":"olp_001"}'
```

✅ **If this works, your core logic is API-ready!**

---

## 📊 MIGRATION ROADMAP

### Phase 1: API Foundation (1-2 weeks)
- [ ] Create FastAPI structure
- [ ] Implement chat endpoint (reuse agent.py)
- [ ] Implement auth with JWT
- [ ] Fix ScenarioManager persistence
- [ ] Write API integration tests

### Phase 2: React Frontend Scaffolding (1 week)
- [ ] Create Next.js/Vite project
- [ ] Implement login page
- [ ] Implement chat UI (WebSocket or polling)
- [ ] Connect to FastAPI backend

### Phase 3: Feature Parity (2-3 weeks)
- [ ] Stats dashboard (analytics API + React charts)
- [ ] Case selection
- [ ] Profile management
- [ ] Image display for findings

### Phase 4: Deprecate Streamlit (1 week)
- [ ] Final testing
- [ ] Deploy React + FastAPI
- [ ] Archive Streamlit pages

**Total Estimated Time:** 5-7 weeks (1 developer, part-time)

---

## 🎓 CONCLUSION

### Migration Difficulty: **MEDIUM** ⚠️

**Why not HIGH?**
- ✅ Core business logic is clean
- ✅ Database models are solid
- ✅ Agent already returns JSON

**Why not LOW?**
- ⚠️ ScenarioManager needs DB refactor
- ⚠️ Auth system needs complete rewrite
- ⚠️ State management philosophy change

### **First Action Items** (Today):

1. **Run the prototype API** (chat_prototype.py above)
2. **Add `state_json` column to StudentSession model**
3. **Test agent.process_student_input() in isolation**

### **Decision Point:**

If you can successfully run the prototype API and get a chat response without any Streamlit imports, you're **80% ready** for migration. The remaining 20% is infrastructure (auth, deployment, React UI).

---

**Next Steps:** Should I create the `chat_prototype.py` file and the database migration for `state_json`? 🚀
