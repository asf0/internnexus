# InternNexus v1.0

A production-ready internship and job aggregator that combines API polling from multiple job boards (Greenhouse, Lever) with intelligent company discovery and advanced filtering.

**Current Status:** 15,000+ jobs from 145+ companies | Full-stack with Next.js + FastAPI + PostgreSQL

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 18+
- PostgreSQL 17 (runs in Docker)

### 1. Start the Database

```bash
docker-compose up -d
```

This starts PostgreSQL 17 with pgvector extension on port 5432.

### 2. Start the Backend API

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run migrations (first time only)
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API available at: `http://localhost:8000`

Health check: `http://localhost:8000/health`

### 3. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend available at: `http://localhost:3000`

---

## 📚 Usage Guide

### Ingesting Jobs

The ingestion system supports two modes: **fast mode** (cached companies) and **discovery mode** (find new companies).

#### Option 1: Fast Ingestion (Use Cached Companies)

```bash
cd backend
python3 run_ingestion_simple.py
```

**What it does:**
- Uses cached companies from previous discovery runs
- Falls back to 18 verified seed companies if no cache exists
- Fetches jobs from Greenhouse and Lever APIs
- Deduplicates jobs (SHA256 fingerprinting)
- Stores in PostgreSQL with automatic batching
- Takes ~1-2 minutes for ~5,000 jobs

**Output:**
```
INFO:__main__:Using cached/seed companies (23 total)
INFO:__main__:Fetched 5083 jobs from APIs
INFO:ingestion.pipeline:Upserted batch 1: 100 jobs (total: 100/5083)
...
INFO:__main__:Ingestion complete!
```

#### Option 2: Discover New Companies (Full Discovery with GitHub Harvesting)

```bash
cd backend
python3 run_ingestion_simple.py --discover
```

**What it does:**
- Harvests company slugs from SimplifyJobs GitHub repos (Summer 2026 + New Grad)
- Tests 190+ company candidates (seed + common + GitHub harvested)
- Verifies which companies have active Greenhouse/Lever job boards
- Uses concurrent requests (10 at a time) for speed
- Automatically caches discovered companies to `ingestion/apis/discovered_companies.json`
- Then fetches all jobs from verified companies
- Takes ~3-5 minutes first run, subsequent runs use cache

**Output:**
```
INFO:ingestion.apis.company_registry:Harvested 131 unique companies from GitHub
INFO:ingestion.apis.company_registry:Total candidates to verify: 194
INFO:ingestion.apis.company_registry:Discovering companies from 194 candidates...
INFO:ingestion.apis.company_registry:✓ Found active board: airbnb
INFO:ingestion.apis.company_registry:✓ Found active board: stripe
...
INFO:ingestion.apis.company_registry:Discovered 145 active job boards
INFO:ingestion.apis.company_registry:Cached 145 companies to discovered_companies.json
INFO:__main__:Using 145 discovered companies for ingestion
INFO:__main__:Fetched 14865 jobs from APIs
INFO:__main__:Ingestion complete!
```

#### Clearing Cache (Force Fresh Discovery)

```bash
rm backend/ingestion/apis/discovered_companies.json
python3 run_ingestion_simple.py --discover
```

### Database Operations

#### Check Job Statistics

```bash
cd backend
python3 -c "
from app.db import SessionLocal
from app.models import Job

with SessionLocal() as db:
    total = db.query(Job).count()
    companies = db.query(Job.company).distinct().count()
    print(f'Total jobs: {total}')
    print(f'Unique companies: {companies}')
"
```

#### Clear Database

```bash
cd backend
python3 -c "
from app.db import SessionLocal
from app.models import Job

with SessionLocal() as db:
    count = db.query(Job).delete()
    db.commit()
    print(f'Deleted {count} jobs')
"
```

---

## 🌐 API Endpoints

### Jobs

**Get all jobs with pagination:**
```bash
curl "http://localhost:8000/jobs?page=1&page_size=20"
```

**Get job by ID:**
```bash
curl "http://localhost:8000/jobs/{job_id}"
```

**Filter jobs:**
```bash
# By search term
curl "http://localhost:8000/jobs?search=python&page=1"

# By company (single)
curl "http://localhost:8000/jobs?company=stripe&page=1"

# By multiple companies
curl "http://localhost:8000/jobs?company=stripe,airbnb&page=1"

# By location
curl "http://localhost:8000/jobs?location=san%20francisco&page=1"

# By job type
curl "http://localhost:8000/jobs?job_type=internship&page=1"

# By work mode
curl "http://localhost:8000/jobs?work_mode=remote&page=1"

# By visa sponsorship
curl "http://localhost:8000/jobs?visa_sponsored=true&page=1"

# By F1 friendly
curl "http://localhost:8000/jobs?f1_friendly=true&page=1"

# Combined filters
curl "http://localhost:8000/jobs?search=engineer&company=stripe&work_mode=remote&visa_sponsored=true&page=1"
```

### Filters

**Get all companies:**
```bash
curl "http://localhost:8000/jobs/filters/companies"
```

**Get all locations:**
```bash
curl "http://localhost:8000/jobs/filters/locations"
```

### Health

**Check API status:**
```bash
curl "http://localhost:8000/health"
```

---

## 🎨 Frontend Features

### Job Listing
- **Pagination:** Navigate through all 5,000+ jobs with Next/Previous buttons
- **Search:** Search by job title, company name, or location
- **Multi-select Filters:** 
  - Companies (select multiple)
  - Locations (select multiple)
  - Job Type (Internship, Full-time, Part-time)
  - Work Mode (Remote, Hybrid, On-site)
  - Visa Sponsorship (checkbox)
  - F1 Friendly (checkbox)
- **Dark Mode:** Toggle between light/dark theme (persisted to localStorage)
- **Real-time Filtering:** Filters update URL and results instantly

### Job Details
- Full job description with formatted HTML
- Company, location, and application link
- Posted date and active status

### Resume Uploader
- Upload PDF resume for future matching (AI enrichment ready)
- Dark mode support

---

## 📁 Project Structure

```
internjobs/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── db.py                # Database connection
│   │   └── api/
│   │       └── jobs.py          # Job endpoints & filtering logic
│   ├── ingestion/
│   │   ├── pipeline.py          # Core ingestion pipeline
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── apis/
│   │       ├── company_registry.py      # Company discovery + caching
│   │       ├── greenhouse_client.py     # Greenhouse API client
│   │       └── lever_client.py          # Lever API client
│   ├── migrations/              # Alembic database migrations
│   ├── run_ingestion_simple.py  # Main ingestion script
│   ├── requirements.txt
│   └── .env                     # Backend config (OPENAI_API_KEY, etc)
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Job listing page
│   │   ├── layout.tsx           # Root layout
│   │   └── jobs/
│   │       └── [id]/
│   │           └── page.tsx     # Job detail page
│   ├── components/
│   │   ├── JobFilters.tsx       # Advanced filtering UI
│   │   ├── MultiSelect.tsx      # Reusable multi-select dropdown
│   │   ├── ThemeToggle.tsx      # Dark mode toggle
│   │   ├── ResumeUploader.tsx   # Resume upload component
│   │   └── Pagination.tsx       # Pagination controls
│   ├── lib/
│   │   └── api.ts              # Backend API client
│   ├── tailwind.config.ts       # Tailwind + dark mode config
│   ├── frontend/.env.local      # Frontend config (BACKEND_URL)
│   └── package.json
└── docker-compose.yml           # PostgreSQL setup
```

---

## 🔧 Configuration

### Backend (.env)

```env
# Database
DATABASE_URL=postgresql://internexus:internexus@localhost:5432/internjobs

# OpenAI (for AI enrichment - optional)
OPENAI_API_KEY=sk-...

# API Keys (optional)
GREENHOUSE_API_KEY=
LEVER_API_KEY=
```

### Frontend (.env.local)

```env
BACKEND_URL=http://localhost:8000
```

---

## 🚀 Deployment

### Frontend (Vercel)

```bash
cd frontend
vercel deploy
```

### Backend (Docker)

```bash
# Build image
docker build -t internjobs-backend:latest -f Dockerfile.backend .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e OPENAI_API_KEY=sk-... \
  internjobs-backend:latest
```

---

## 📊 Data

### Current Database
- **Total Jobs:** 15,000+
- **Companies:** 145
- **Locations:** 1,000+
- **Deduplication:** SHA256 fingerprinting (company|title|location)
- **Data Source:** SimplifyJobs GitHub repos (Summer 2026 + New Grad) + Seed companies

### Company Discovery
The system automatically harvests company data from:
1. **SimplifyJobs GitHub Repos** (131 companies):
   - Summer 2026 Internships: https://github.com/SimplifyJobs/Summer2026-Internships
   - New Grad 2026 Positions: https://github.com/SimplifyJobs/New-Grad-Positions
2. **Seed Companies** (18 verified):
   - Airbnb, Airtable, Amplitude, Brex, Cloudflare, Coinbase, Databricks, Datadog, Discord, Elastic, Figma, GitLab, Okta, Plaid, Robinhood, Roblox, Stripe, Twilio
3. **Common Tech Companies** (additional candidates)

### Verified Companies (Sample)
10xGenomics, Accuweather, Affirm, Airbnb, Airtable, AloyogaHealth, Amplitude, Astra Robotics, Bandwidth, Brex, Cloudflare, Coinbase, Databricks, Datadog, Discord, Elastic, Figma, GitLab, Okta, Plaid, and 125+ more...

---

## 🔄 Data Update Strategy

### Daily Updates (Fast)
```bash
# Morning cron job - uses cached companies
0 8 * * * cd /path/to/backend && python3 run_ingestion_simple.py
```

### Weekly Discovery (Full)
```bash
# Weekly Monday morning - discovers new companies
0 8 * * 1 cd /path/to/backend && python3 run_ingestion_simple.py --discover
```

---

## 🧪 Testing

### Test Backend Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### Test Job Fetching

```bash
curl http://localhost:8000/jobs?page=1 | python3 -m json.tool | head -50
```

### Test Filtering

```bash
# Search + company + remote
curl "http://localhost:8000/jobs?search=engineer&company=stripe&work_mode=remote&page=1"
```

---

## 📝 Advanced Features (Coming Soon)

- **AI Enrichment:** Auto-detect visa sponsorship, F1 friendly status, and job embeddings
- **LinkedIn/Indeed Scraping:** Add thousands more jobs via web scraping
- **Resume Matching:** Match uploaded resume against job descriptions
- **Email Alerts:** Subscribe to job alerts based on filters
- **Analytics:** Track job market trends

---

## 🐛 Troubleshooting

### Database Connection Error
```
Error: could not connect to server: Connection refused
```
**Solution:** Start Docker: `docker-compose up -d`

### Port Already in Use
```
Error: Address already in use
```
**Solution:** Kill existing process or change port
```bash
# Port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Port 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

### No Jobs Found
```
GET /jobs returns empty results
```
**Solution:** Run ingestion
```bash
cd backend
python3 run_ingestion_simple.py
```

### Frontend Can't Connect to Backend
```
Error: fetch failed (Cannot GET http://localhost:8000/jobs)
```
**Solution:** Check frontend/.env.local
```env
BACKEND_URL=http://localhost:8000
```

---

## 📄 License

MIT

---

## 👨‍💻 Development

### Add New Company to Seed List

1. Edit `backend/ingestion/apis/company_registry.py`
2. Add slug to `SEED_COMPANIES` list
3. Re-run ingestion: `python3 run_ingestion_simple.py`

### Update API Filters

1. Edit `backend/app/api/jobs.py` to add new filter parameter
2. Update `frontend/lib/api.ts` to pass new filter
3. Update `frontend/components/JobFilters.tsx` to add UI control

### Add Database Fields

1. Create migration: `alembic revision --autogenerate -m "Add field"`
2. Update `backend/app/models.py` with new field
3. Update API schema in `backend/ingestion/schemas.py`
4. Run migration: `alembic upgrade head`

---

## 📞 Support

For issues or questions:
1. Check Troubleshooting section above
2. Review API endpoint documentation
3. Check backend logs: `docker-compose logs db`
   - Stealth scraping for LinkedIn + Indeed
   - Deduplication by fingerprint and upsert
3. **AI Intelligence Layer**
   - Visa sponsorship classification
   - Description embeddings with text-embedding-3-small
4. **Frontend Architecture (Next.js 16)**
   - Server components for listings and job detail
   - Resume upload and matching flow
   - Shadcn UI data grid and filters
5. **API & Orchestration**
   - FastAPI endpoints for listing and matching
   - Scheduler for ingestion pipeline
