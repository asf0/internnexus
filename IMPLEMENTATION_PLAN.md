# InternNexus Implementation Plan

## Enhanced Profile & Matching System

---

### **PHASE 1: Resume Storage + Profile Enhancement** (2 hours)

#### **Database Changes** (`backend/app/models.py`)

**Add to User model:**
```python
# Resume storage
resume_text = Column(Text, nullable=True)
resume_embedding = Column(Vector(1024), nullable=True)
resume_filename = Column(String(255), nullable=True)
resume_uploaded_at = Column(DateTime(timezone=True), nullable=True)

# Enhanced profile for filtering
experience_level = Column(
    Enum('junior', 'mid', 'senior', name='experience_level_enum'),
    nullable=True
)
salary_min = Column(Integer, nullable=True)  # Annual USD
salary_max = Column(Integer, nullable=True)
job_type_preference = Column(
    Enum('internship', 'full_time', 'part_time', 'contract', name='job_type_enum'),
    nullable=True
)
work_mode_preference = Column(
    Enum('remote', 'hybrid', 'onsite', name='work_mode_enum'),
    nullable=True
)
industry_preferences = Column(ARRAY(String), nullable=True)  # PostgreSQL array
```

#### **New Files to Create:**

1. **`backend/app/services/resume_service.py`** - Resume storage service
2. **`backend/app/api/resume.py`** - Resume endpoints
3. **Migration file** - Alembic migration for new columns

#### **API Endpoints to Add:**

```python
# Resume management
POST   /users/me/resume          # Upload resume (PDF)
GET    /users/me/resume          # Get resume metadata
DELETE /users/me/resume          # Remove resume
GET    /users/me/resume/download # Download resume file

# Enhanced profile
PUT    /users/me/profile         # Update profile with new fields
```

#### **Frontend Changes:**

1. **`frontend/app/settings/page.tsx`** - Add sections:
   - Resume upload/management
   - Experience level dropdown
   - Salary range inputs (min/max)
   - Job type preferences
   - Work mode preferences
   - Industry multi-select

2. **`frontend/app/actions/user.ts`** - Add:
   - `uploadResume()` action
   - `deleteResume()` action
   - Update `updateUserProfile()` with new fields

#### **Implementation Steps:**

1. **Create Alembic migration** (10 min)
   ```bash
   cd backend && alembic revision -m "add_resume_and_profile_fields"
   ```

2. **Update User model** (5 min)

3. **Create resume service** (`backend/app/services/resume_service.py`) (15 min)
   - Save file to `/app/resumes/{user_id}/{filename}`
   - Extract text using existing pdf extraction
   - Generate embedding using embedding_service

4. **Create resume API endpoints** (`backend/app/api/resume.py`) (15 min)
   - File upload endpoint
   - File download endpoint
   - Delete endpoint

5. **Update user API** (`backend/app/api/users.py`) (10 min)
   - Extend PUT /users/me to handle new fields

6. **Frontend settings page updates** (45 min)
   - Add resume upload component
   - Add profile preference form fields

---

### **PHASE 2: Enhanced Matching + Password Reset** (2 hours)

#### **Enhanced Matching Endpoint**

**New file:** `backend/app/api/matching_enhanced.py`

```python
POST /match/profile
{
  "filters": {
    "work_mode": ["remote", "hybrid"],
    "salary_min": 80000,
    "job_type": "full_time",
    "experience_level": "mid",
    "locations": ["San Francisco", "Remote"]
  },
  "max_results": 50,
  "min_score": 0.5
}
```

**Query logic:**
1. Filter jobs with SQL WHERE clauses
2. Calculate cosine similarity on filtered subset
3. Rank by combined score

#### **Redis Queue for Async Processing**

**New file:** `backend/app/services/queue_service.py`
- Store embedding generation jobs
- Background worker to process resume uploads

#### **Password Reset with SendGrid**

**New files:**
1. `backend/app/services/email_service.py` - SendGrid integration
2. `backend/app/api/auth.py` - Add endpoints:
   - `POST /auth/forgot-password`
   - `POST /auth/reset-password`

**Database addition:**
```python
# PasswordResetToken model
user_id = ForeignKey
token = String (hashed)
expires_at = DateTime
used = Boolean
```

**Frontend:**
- `frontend/app/forgot-password/page.tsx`
- `frontend/app/reset-password/page.tsx` (with token from URL)

---

### **TECHNICAL NOTES**

#### **File Storage:**
- Resumes stored at: `/app/resumes/{user_id}/{uuid}_{filename}`
- Environment variable: `RESUME_STORAGE_PATH=/app/resumes`

#### **SendGrid Setup:**
1. Sign up: https://sendgrid.com (free tier: 100 emails/day)
2. Create API key
3. Add to `.env`: `SENDGRID_API_KEY=SG.xxx`

#### **Database Migrations:**
```bash
# Generate migration
cd backend
alembic revision -m "add_resume_and_profile_fields"

# Run migration
alembec upgrade head
```

#### **Testing Checklist:**
- [ ] Upload resume works
- [ ] Resume embedding generated
- [ ] Profile updates persist
- [ ] Matching uses stored resume
- [ ] Filters work correctly
- [ ] Password reset email sends
- [ ] Password reset token validates
- [ ] Redis queue processes jobs

---

### **RESUME IMPACT**

**Phase 1 demonstrates:**
- File upload handling
- Local storage management
- Database schema design
- User profile management

**Phase 2 demonstrates:**
- Hybrid search (vector + metadata)
- Background job processing
- Email service integration
- Authentication security
- Redis caching/queuing

---

### **FOOTER IMPLEMENTATION**

**Links to Add:**
- About
- GitHub (personal profile)
- LinkedIn (your profile)
- Contact/Support

**Style:** Styled component with social icons
- Dark/light mode compatible
- Mobile responsive
- Professional design

**Location:** `frontend/app/components/Footer.tsx`

---

## **Ready to start Phase 1 when you are!**

**Next session priorities:**
1. Create footer component (quick win, 30 min)
2. Start Phase 1: Resume storage (2 hours)
3. Or start Phase 1 and do footer after

**Current status before this work:**
- MVP: 97%
- Production: 82%
- Docker health checks: ✅
- Structured logging: ✅
- CORS security: ✅ (environment-based)