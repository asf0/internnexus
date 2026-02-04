# Job Ingestion Pipeline

A comprehensive pipeline for fetching, processing, and embedding job postings from multiple sources.

## Overview

The pipeline runs 4 sequential steps:

| Step | Name | Description |
|------|------|-------------|
| 1 | **Discover** | Verify companies have active Greenhouse/Lever job boards |
| 2 | **Ingest** | Fetch jobs from APIs, enrich with metadata, deduplicate & upsert |
| 3 | **Cleanup** | Normalize location data (city, state, country) |
| 4 | **Embed** | Generate vector embeddings for job matching |

## Quick Start

```bash
cd backend

# Run full pipeline once
python run_pipeline.py

# Run without company discovery (faster)
python run_pipeline.py --skip-discover

# Run continuously every hour
python run_pipeline.py --continuous --interval 3600
```

## Usage

### Full Pipeline

```bash
# Run all 4 steps
python run_pipeline.py

# Skip company discovery (recommended for regular runs)
python run_pipeline.py --skip-discover
```

### Individual Steps

```bash
# Only discover companies with active job boards
python run_pipeline.py --step discover

# Only fetch and ingest new jobs
python run_pipeline.py --step ingest

# Only cleanup/normalize locations
python run_pipeline.py --step cleanup

# Only generate embeddings for jobs without them
python run_pipeline.py --step embed
```

### Continuous Mode

```bash
# Run every hour (default)
python run_pipeline.py --continuous

# Run every 30 minutes
python run_pipeline.py --continuous --interval 1800

# Run every 6 hours, skip discovery
python run_pipeline.py -c -i 21600 --skip-discover
```

### Cron Setup

Add to crontab for scheduled runs:

```bash
# Edit crontab
crontab -e

# Run every hour
0 * * * * cd /path/to/backend && /path/to/venv/bin/python run_pipeline.py --skip-discover >> /var/log/job-pipeline.log 2>&1

# Run every 6 hours
0 */6 * * * cd /path/to/backend && /path/to/venv/bin/python run_pipeline.py --skip-discover >> /var/log/job-pipeline.log 2>&1

# Run daily at 2am
0 2 * * * cd /path/to/backend && /path/to/venv/bin/python run_pipeline.py >> /var/log/job-pipeline.log 2>&1
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--continuous` | `-c` | Run continuously instead of once |
| `--interval SECONDS` | `-i` | Interval between runs (default: 3600) |
| `--step STEP` | | Run only: `discover`, `ingest`, `cleanup`, or `embed` |
| `--skip-discover` | | Skip company discovery step (faster) |

## Pipeline Steps Explained

### Step 1: Discover Companies

Verifies which companies have active job boards on Greenhouse or Lever.

- Checks the company registry + additional known companies
- Rate-limited to 5 concurrent requests
- Companies without active boards are skipped during ingestion

**When to run:** Weekly or when adding new companies

### Step 2: Fetch & Ingest Jobs

Fetches jobs from all configured sources and upserts to database.

- **Sources:** Greenhouse API, Lever API
- **Enrichment:** Visa sponsorship, F1 friendly, job categories
- **Deduplication:** Uses fingerprint hash of `company|title|location`
- **Upsert:** New jobs are inserted, existing jobs update `last_seen` timestamp

**Deduplication Logic:**
```
fingerprint = SHA256(company.lower() + "|" + title.lower() + "|" + location.lower())
```

Jobs with the same fingerprint are considered duplicates. On conflict:
- `last_seen` is updated to current time
- `is_active` is set to `True`

### Step 3: Cleanup Locations

Normalizes location data for consistent filtering.

**Transformations:**
- `San Francisco, CA` → city: "San Francisco", state: "CA", country: "United States"
- `NYC, New York` → city: "NYC", state: "NY", country: "United States"
- `London, UK` → city: "London", country: "United Kingdom"
- `Remote` → country: "Remote"

**Supported:**
- All US states (abbreviations and full names)
- Common country aliases (US, USA, UK, etc.)

### Step 4: Generate Embeddings

Creates vector embeddings for jobs that don't have them.

- **Provider:** Configurable (Ollama or OpenAI)
- **Model:** `nomic-embed-text` (768 dimensions) or `text-embedding-3-small`
- **Batch commits:** Every 50 jobs
- **Text cleaning:** Removes HTML, truncates to 4000 chars

**Required for:** Resume matching feature

## Configuration

### Environment Variables

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=internjobs
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword

# Embedding Provider
EMBEDDING_PROVIDER=ollama          # or "openai"
EMBEDDING_MODEL=nomic-embed-text   # or "text-embedding-3-small"
OLLAMA_BASE_URL=http://localhost:11434

# Optional: OpenAI (if using openai provider)
OPENAI_API_KEY=sk-...
```

### Company Registry

Companies are configured in `ingestion/apis/company_registry.py`:

```python
COMPANY_REGISTRY: list[str] = [
    "airbnb",
    "stripe",
    "netflix",
    # ... add company slugs
]
```

**Finding company slugs:**
- Greenhouse: `https://boards.greenhouse.io/{slug}`
- Lever: `https://jobs.lever.co/{slug}`

## Output Example

```
2026-02-03 10:00:00 [INFO] ============================================================
2026-02-03 10:00:00 [INFO] PIPELINE START - 2026-02-03 10:00:00
2026-02-03 10:00:00 [INFO] ============================================================
2026-02-03 10:00:00 [INFO] ============================================================
2026-02-03 10:00:00 [INFO] STEP 1: Discovering companies with active job boards...
2026-02-03 10:00:00 [INFO] ============================================================
2026-02-03 10:00:00 [INFO] Verifying 75 company slugs...
2026-02-03 10:00:05 [INFO] Found 62 active job boards
2026-02-03 10:00:05 [INFO] ============================================================
2026-02-03 10:00:05 [INFO] STEP 2: Fetching and ingesting jobs...
2026-02-03 10:00:05 [INFO] ============================================================
2026-02-03 10:00:05 [INFO] Loading category context...
2026-02-03 10:00:05 [INFO] Fetching from Greenhouse and Lever APIs...
2026-02-03 10:01:30 [INFO] Fetched 1,247 jobs from APIs
2026-02-03 10:01:30 [INFO] Enriching jobs with visa/F1 info and categories...
2026-02-03 10:01:31 [INFO] Upserting to database (duplicates will be skipped)...
2026-02-03 10:01:35 [INFO] Deduped 89 jobs within batch (1,158 unique)
2026-02-03 10:01:40 [INFO] Ingestion complete: 1,247 jobs processed
2026-02-03 10:01:40 [INFO] ============================================================
2026-02-03 10:01:40 [INFO] STEP 3: Cleaning up locations...
2026-02-03 10:01:40 [INFO] ============================================================
2026-02-03 10:01:41 [INFO] Found 8,542 active jobs to process
2026-02-03 10:01:45 [INFO] Updated 156 job locations
2026-02-03 10:01:45 [INFO] ============================================================
2026-02-03 10:01:45 [INFO] STEP 4: Generating embeddings...
2026-02-03 10:01:45 [INFO] ============================================================
2026-02-03 10:01:45 [INFO] Found 203 jobs without embeddings
2026-02-03 10:01:45 [INFO] Using embedding provider: ollama
2026-02-03 10:03:20 [INFO] Embedding complete: 201 success, 2 errors
2026-02-03 10:03:20 [INFO] ============================================================
2026-02-03 10:03:20 [INFO] PIPELINE COMPLETE - 200.5s (3.3 min)
2026-02-03 10:03:20 [INFO]   Companies verified: 62
2026-02-03 10:03:20 [INFO]   Jobs fetched: 1,247
2026-02-03 10:03:20 [INFO]   Locations cleaned: 156
2026-02-03 10:03:20 [INFO]   Embeddings generated: 201
2026-02-03 10:03:20 [INFO]   Embedding errors: 2
2026-02-03 10:03:20 [INFO] ============================================================
```

## Troubleshooting

### Embedding Errors

**"Ollama connection failed"**
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Verify `OLLAMA_BASE_URL` in `.env`
- Ensure `nomic-embed-text` model is pulled: `ollama pull nomic-embed-text`

**"Failed to initialize embedding service"**
- Check environment variables are set
- For OpenAI: verify `OPENAI_API_KEY` is valid

### Database Errors

**"Connection refused"**
- Check PostgreSQL is running
- Verify database credentials in `.env`

### No Jobs Fetched

- Run `python run_pipeline.py --step discover` to check active boards
- Check network connectivity to greenhouse.io and lever.co
- Review company registry for valid slugs

## File Structure

```
backend/
├── run_pipeline.py          # Main pipeline script
├── embed_jobs.py            # Standalone embedding script
├── cleanup_locations.py     # Standalone location cleanup
├── discover_companies.py    # Standalone company discovery
├── ingestion/
│   ├── pipeline.py          # Core fetch/upsert logic
│   ├── enrichment.py        # Visa/F1/category enrichment
│   ├── schemas.py           # Job data schemas
│   └── apis/
│       ├── company_registry.py   # Company slug list
│       ├── greenhouse_client.py  # Greenhouse API client
│       └── lever_client.py       # Lever API client
└── app/
    └── services/
        └── embedding_service.py  # Ollama/OpenAI embeddings
```

## Recommended Schedule

| Use Case | Schedule | Command |
|----------|----------|---------|
| Development | Manual | `python run_pipeline.py --skip-discover` |
| Production | Every 6 hours | `python run_pipeline.py -c -i 21600 --skip-discover` |
| Full refresh | Weekly | `python run_pipeline.py` (with discovery) |
| Embedding only | As needed | `python run_pipeline.py --step embed` |
