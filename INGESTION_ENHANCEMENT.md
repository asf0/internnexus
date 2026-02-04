# Job Ingestion Enhancement - Summary

## Overview
Updated the job ingestion system to:
1. **Extract job categories** from SimplifyJobs markdown files (organized by emoji sections)
2. **Detect legend attributes** (sponsorship, citizenship, closed applications, FAANG+, advanced degree requirements)
3. **Avoid database nulls** by intelligently parsing and categorizing jobs during ingestion

## Changes Made

### 1. Database Schema (Updated)
- **New Enum**: `JobCategory` with values:
  - Software Engineering
  - Product Management
  - Data Science, AI & Machine Learning
  - Quantitative Finance
  - Hardware Engineering

- **New Columns** in `jobs` table:
  - `job_category`: VARCHAR (ENUM)
  - `requires_sponsorship`: BOOLEAN (🛂 Does NOT offer sponsorship)
  - `requires_us_citizenship`: BOOLEAN (🇺🇸 Requires U.S. Citizenship)
  - `application_closed`: BOOLEAN (🔒 Application is closed)
  - `is_faang_plus`: BOOLEAN (🔥 FAANG+ company)
  - `requires_advanced_degree`: BOOLEAN (🎓 Advanced degree required)

### 2. Backend Models & Schemas
**File**: `backend/app/models.py`
- Added `JobCategory` enum
- Updated `Job` model with 6 new columns

**File**: `backend/app/api/schemas.py`
- Updated `JobResponse` to include all new fields

**File**: `backend/ingestion/schemas.py`
- Added `JobCategory` type definition
- Extended `JobSchema` with new fields

### 3. Ingestion Enrichment Pipeline
**File**: `backend/ingestion/enrichment.py`

New classes:
- **`LegendAttributeDetector`**: Detects legend attributes from job descriptions
  - `detect_requires_sponsorship()`: Looks for "no sponsorship" patterns
  - `detect_requires_us_citizenship()`: Detects citizenship requirements
  - `detect_application_closed()`: Detects closed applications
  - `detect_is_faang_plus()`: Known FAANG+ company list
  - `detect_requires_advanced_degree()`: Detects Master's/PhD requirements

- **`CategoryDetector`**: Auto-detects job category
  - Software Engineering: "software", "engineer", "developer", etc.
  - Product Management: "product", "pm", "manager"
  - Data Science & AI: "data", "machine learning", "analytics"
  - Quantitative Finance: "quant", "trading", "finance"
  - Hardware Engineering: "hardware", "firmware", "embedded", etc.

Updated `enrich_jobs()` to:
- Accept optional `category_context` dict from markdown parser
- Detect all legend attributes
- Assign job categories

### 4. SimplifyJobs Markdown Parser
**File**: `backend/ingestion/apis/simplify_jobs_parser.py` (NEW)

- **`SimplifyJobsCategoryParser`**: Parses SimplifyJobs README files
  - Extracts job categories from emoji-based section headers
  - Maps companies to their categories
  - Supports both Summer 2026 and New Grad job listings
  - Runs async for performance

- **`get_category_context()`**: Helper function to get all categories

### 5. Database Ingestion Pipeline
**File**: `backend/ingestion/pipeline.py`
- Updated `upsert_jobs()` to handle new fields

**File**: `backend/run_ingestion.py`
- Now fetches category context from SimplifyJobs markdown
- Passes context to enrichment pipeline
- Logs category extraction progress

### 6. Database Migration
**File**: `backend/alembic/versions/20260203_000002_add_job_attributes.py`
- Alembic migration that adds the 6 new columns to `jobs` table
- Includes rollback support

### 7. Frontend Updates
**File**: `frontend/lib/types.ts`
- Updated `Job` interface with all new fields

**File**: `frontend/components/JobFilters.tsx`
- Added job category filter (multi-select)
- Added expandable legend with all 5 badge meanings

**File**: `frontend/components/JobBadges.tsx` (NEW)
- Displays appropriate badges for each job
- Shows icons and labels based on legend attributes

**File**: `frontend/app/page.tsx`
- Updated search params to include category filter
- Displays job category below company/location
- Uses new JobBadges component

**File**: `frontend/lib/api.ts`
- Updated `JobFilters` interface with category parameter
- Passes category to API requests

## How It Works

### During Ingestion
1. **Fetch Jobs**: Get jobs from Greenhouse, Lever, and other sources
2. **Parse Categories**: Extract categories from SimplifyJobs markdown (emoji-based sections)
3. **Enrich**: 
   - Detect legend attributes from job descriptions
   - Auto-detect category if not found in context
   - Classify visa sponsorship and F1 status
   - Generate embeddings
4. **Store**: Save to database with all attributes (no nulls for defaults)

### Categories Detected From Markdown
The parser reads SimplifyJobs README files and extracts categories based on section headers:
- `## 💻 Software Engineering Internship Roles` → Software Engineering
- `## 📱 Product Management Internship Roles` → Product Management
- `## 🤖 Data Science, AI & Machine Learning` → Data Science, AI & Machine Learning
- `## 📈 Quantitative Finance Internship Roles` → Quantitative Finance
- `## 🔧 Hardware Engineering Internship Roles` → Hardware Engineering

### Legend Attributes Detected
Pattern matching on job descriptions for:
- **🛂**: "does not offer sponsorship", "no sponsorship"
- **🇺🇸**: "u.s. citizenship", "citizenship required"
- **🔒**: "application closed", "not accepting"
- **🔥**: Pre-defined list of FAANG+ companies
- **🎓**: "master's degree", "phd required", "graduate student"

## Running the Migration

```bash
cd backend
alembic upgrade head
```

## Running Ingestion

```bash
cd backend
python run_ingestion.py
```

The ingestion will now:
1. Fetch SimplifyJobs categories
2. Ingest jobs with all attributes populated
3. No more null values for job categories and legend attributes (intelligent defaults based on parsing)

## Testing

To test the category parser independently:
```python
from ingestion.apis.simplify_jobs_parser import get_category_context
categories = get_category_context()
print(categories)  # Dict of company -> category
```

To test attribute detection:
```python
from ingestion.enrichment import LegendAttributeDetector
detector = LegendAttributeDetector()
result = detector.detect_requires_sponsorship("this job does not offer sponsorship", "")
print(result)  # True
```
