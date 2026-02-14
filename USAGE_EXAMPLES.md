# Job Ingestion Enhancement - Usage Examples

## Database Examples

### Sample Enriched Job (after ingestion)

```sql
SELECT 
  id,
  title,
  company,
  location,
  job_category,
  visa_sponsored,
  f1_friendly,
  requires_sponsorship,
  requires_us_citizenship,
  application_closed,
  is_faang_plus,
  requires_advanced_degree
FROM jobs
WHERE company = 'Google'
LIMIT 1;
```

**Result:**
```
id                                   | F3B2A1D4-...
title                                | Software Engineer Intern
company                              | Google
location                             | Mountain View, CA
job_category                         | Software Engineering  ← Auto-detected from title
visa_sponsored                       | true                   ← From CV classifier
f1_friendly                          | true                   ← From CV classifier
requires_sponsorship                 | false                  ← Pattern matched description
requires_us_citizenship              | false                  ← No citizenship requirement found
application_closed                   | false                  ← Application still open
is_faang_plus                        | true                   ← FAANG+ company list
requires_advanced_degree             | false                  ← Not a PhD/Master's role
```

### Another Example (Data Science Role)

```sql
SELECT title, company, job_category, requires_advanced_degree, is_faang_plus
FROM jobs
WHERE title LIKE '%Data Science%'
LIMIT 1;
```

**Result:**
```
title                                | Research Intern - AI/ML (PhD)
company                              | Microsoft
job_category                         | Data Science, AI & Machine Learning
requires_advanced_degree             | true   ← Detected "PhD" in title
is_faang_plus                        | true   ← Microsoft is FAANG+
```

## Frontend Examples

### Filter by Category

Users can now filter jobs by category:
- 💻 Software Engineering (318)
- 📱 Product Management (98)
- 🤖 Data Science, AI & Machine Learning (635)
- 📈 Quantitative Finance (7)
- 🔧 Hardware Engineering (174)

### Job Card Display

```
┌─────────────────────────────────────────────────┐
│ Software Engineer Intern                        │
│ Google • Mountain View, CA                      │
│ Software Engineering                            │
│                                                 │
│ ✅ Visa Sponsored  ✅ F1 Friendly  🔥 FAANG+   │
└─────────────────────────────────────────────────┘
```

### Legend Popup

When users click the Legend button, they see:
```
Legend
▼
🛂 Does NOT offer sponsorship
🇺🇸 Requires U.S. Citizenship
🔒 Internship application is closed
🔥 FAANG+ company
🎓 Advanced degree required (Master's, PhD, MBA)
```

## Programmatic Usage

### Accessing Enriched Data in Python

```python
from app.db import SessionLocal
from app.models import Job

db = SessionLocal()

# Get all Data Science roles
data_science_jobs = db.query(Job).filter(
    Job.job_category == "Data Science, AI & Machine Learning"
).all()

# Get all FAANG+ companies with visa sponsorship
faang_visa = db.query(Job).filter(
    Job.is_faang_plus == True,
    Job.visa_sponsored == True
).all()

# Get roles that don't require US citizenship
no_citizenship = db.query(Job).filter(
    Job.requires_us_citizenship == False
).all()

# Get open PhD positions
phd_jobs = db.query(Job).filter(
    Job.requires_advanced_degree == True,
    Job.application_closed == False
).all()
```

### API Response Example

**GET** `/jobs?category=Software%20Engineering&is_faang_plus=true`

```json
{
  "items": [
    {
      "id": "f3b2a1d4-...",
      "title": "Software Engineer Intern",
      "company": "Google",
      "location": "Mountain View, CA",
      "apply_url": "...",
      "description_text": "...",
      "visa_sponsored": true,
      "f1_friendly": true,
      "job_category": "Software Engineering",
      "requires_sponsorship": false,
      "requires_us_citizenship": false,
      "application_closed": false,
      "is_faang_plus": true,
      "requires_advanced_degree": false,
      "posted_at": "2026-02-03T...",
      "is_active": true
    }
  ],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```

## Ingestion Statistics

After running `python run_ingestion.py`, you'll see logs like:

```
INFO:ingestion.apis.company_registry:Harvested 1,234 unique companies from GitHub
INFO:ingestion.apis.simplify_jobs_parser:Parsing SimplifyJobs category data...
INFO:ingestion.apis.simplify_jobs_parser:Total company-category mappings: 856
INFO:ingestion.enrichment:Enriching 3,456 jobs...
  • 1,245 jobs detected as Software Engineering
  • 342 jobs detected as Data Science, AI & Machine Learning
  • 156 jobs detected as Product Management
  • 87 jobs detected as Hardware Engineering
  • 54 jobs detected as Quantitative Finance
INFO:ingestion.pipeline:Upserted batch 1: 100 jobs (total: 100/3456)
INFO:ingestion.pipeline:Upserted batch 2: 100 jobs (total: 200/3456)
...
INFO:ingestion.pipeline:Deduped 234 jobs within batch (3456 unique)
✓ Ingestion complete - 3,456 jobs enriched with categories and attributes
```

## How Categories Are Determined

### 1. From SimplifyJobs Markdown (Most Accurate)
If a company appears in SimplifyJobs README under a specific category header, it gets that category. Example:

```markdown
## 💻 Software Engineering Internship Roles

| Company | Role | Location |
|---------|------|----------|
| Google | Software Engineer Intern | Mountain View |
```
→ Google's jobs get `job_category = "Software Engineering"`

### 2. From Title/Description Pattern Matching (Fallback)
If not found in SimplifyJobs, patterns are matched:
```
title="ML Engineer" → "Data Science, AI & Machine Learning"
title="Product Manager" → "Product Management"
title="Hardware Test Engineer" → "Hardware Engineering"
```

### 3. Database Never Has Nulls
Every job gets a category - either from context or from patterns. No more data quality issues!

## Performance Notes

- SimplifyJobs markdown parsing is **async** and cached
- Category detection runs in **parallel** during enrichment
- Pattern matching is **regex-optimized** for speed
- Database inserts are **batched** (100 jobs per batch)

Typical ingestion time for ~3,500 jobs: **45-90 seconds**

## Filtering by Attributes in Frontend

Users can now use these filters together:

```
Category: Software Engineering
Visa Sponsored: Yes
FAANG+ Only: Yes
Search: "machine learning"
```

This combines:
- Category filter (from `job_category`)
- Visa filter (from `visa_sponsored`)
- FAANG filter (from `is_faang_plus`)
- Text search (from titles/descriptions)

All with **zero null values** for categorical fields!

## Search Syntax

InternNexus supports advanced search syntax for precise job filtering.

### Simple Search (Default)

```
python
```
Uses hybrid search: keyword matching (ILIKE) + semantic search (vector embeddings).
Results are merged and ranked by relevance. Keyword matches get a small boost.

### Boolean Operators

| Query | Meaning |
|-------|---------|
| `python AND remote` | Jobs containing both "python" AND "remote" |
| `python OR java` | Jobs containing either "python" OR "java" |
| `python NOT senior` | Jobs with "python" but NOT "senior" |
| `(python OR java) AND remote` | Grouping with parentheses |

When boolean operators are detected, only keyword search is used (no vector search).

### Exact Phrase Matching

```
"software engineer"
```
Matches the exact phrase "software engineer" (not individual words).

### Field-Specific Search

| Query | Searches In |
|-------|-------------|
| `title:python` | Job title only |
| `company:google` | Company name only |
| `location:remote` | Location field only |
| `description:ml` | Job description only |

### Combined Examples

```
# Python roles at FAANG companies, remote, not senior
title:python AND (google OR meta OR apple) AND remote NOT senior

# Data science or ML roles, visa sponsored
("data science" OR "machine learning") AND visa

# Software engineer internships at startups
title:"software engineer" AND title:intern NOT (google OR meta)
```

### Search Performance Tips

- **Boolean queries** are faster (no vector search needed)
- **Exact phrases** are faster than fuzzy matches
- **Field-specific** searches are more precise
- Popular searches are **cached in Redis** for 24h
- Keyword + semantic hybrid provides best relevance
