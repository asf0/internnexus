from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, or_, case, literal
from sqlalchemy.orm import Session

from app.api.schemas import JobListResponse, JobResponse
from app.db import get_db
from app.models import Job

router = APIRouter()


def extract_job_type(title: str) -> str | None:
    """Extract job type from title."""
    title_lower = title.lower()
    if re.search(r'\bintern\b|\binternship\b', title_lower):
        return "internship"
    elif re.search(r'\bpart[\s-]?time\b', title_lower):
        return "part-time"
    elif re.search(r'\bfull[\s-]?time\b|\bfte\b', title_lower):
        return "full-time"
    return None


def extract_work_mode(title: str, location: str) -> str | None:
    """Extract work mode from title or location."""
    combined = f"{title} {location}".lower()
    if re.search(r'\bremote\b', combined):
        return "remote"
    elif re.search(r'\bhybrid\b', combined):
        return "hybrid"
    elif re.search(r'\bon[\s-]?site\b|\bin[\s-]?office\b', combined):
        return "on-site"
    return None


def normalize_location(location: str) -> str | None:
    """Normalize location by extracting city/region name."""
    if not location or location.strip() == "":
        return None
    
    location = location.strip()
    
    # Skip if it looks like a full street address (starts with number or contains street terms)
    if (re.match(r'^\d+', location) or 
        any(term in location.lower() for term in ['avenue', 'street', 'pkwy', 'blvd', 'drive', 'suite', 'floor'])):
        return None
    
    # Remove parentheses and content inside
    location = re.sub(r'\([^)]*\)', '', location).strip()
    
    # Skip placeholder/generic locations
    skip_patterns = ["add location here", "amer", "amer - us", "tbd", "varies", "multiple", "unknown", "any", "any location",
                     "manager", "associate", "coordinator", "staff", "role", "position", "office", "campus", "hq", "headquarters"]
    if location.lower() in skip_patterns or any(x in location.lower() for x in skip_patterns):
        return None
    
    # Handle remote/flexible locations
    if any(x in location.lower() for x in ["remote", "flexible", "anywhere"]):
        if "remote" in location.lower():
            return "Remote"
        return None
    
    # Skip if location only lists multiple options
    if " or " in location.lower():
        return None
    
    # Clean up weird characters and separators
    location = re.sub(r'[/\\|]+', ' ', location)  # Replace slashes and pipes with space
    location = re.sub(r'\s*-\s*', ', ', location)  # Replace dashes with commas for consistency
    
    # Extract the first city from comma-separated or semicolon-separated lists
    separators = [";", ","]
    for sep in separators:
        if sep in location:
            parts = [p.strip() for p in location.split(sep)]
            location = parts[0]
            break
    
    location = location.strip()
    
    # Skip very long locations (likely multi-location listings)
    if len(location) > 100:
        return None
    
    # Skip if it's too short
    if len(location) < 2:
        return None
    
    # Skip if location looks like corrupted data
    if not re.search(r'[a-zA-Z]', location):
        return None
    
    # Normalize spaces and collapse multiple spaces
    location = re.sub(r'\s+', ' ', location).strip()
    
    # Skip country-only locations (too broad for filtering)
    country_patterns = ["usa", "united states", "canada", "uk", "united kingdom", "india", "australia", "germany", "france",
                        "central,", "northeast,", "southeast,", "midwest", "western ", "eastern ",
                        "united stated", "us canada"]  # Also filter corrupted entries
    if any(location.lower().startswith(p) or location.lower().endswith(p) for p in country_patterns):
        return None
    
    # Extract city and state more robustly
    # Look for 2-letter state code at end (after space, comma, or just before end)
    match = re.match(r'^(.+?)\s*[,\s]+([A-Z]{2})(?:\s|,|$)', location)
    if match:
        city_part = match.group(1).strip()
        state_code = match.group(2).strip()
        # Only keep state if city part is reasonable (actual city name, not just abbreviation)
        if len(city_part) > 2 and not re.match(r'^[A-Z]{2,3}$', city_part):
            location = f"{city_part}, {state_code}"
        else:
            location = city_part
    
    # Proper title case
    location = location.title()
    
    return location


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    company: str | None = Query(None),
    location: str | None = Query(None),
    category: str | None = Query(None),
    visa_sponsored: bool | None = Query(None),
    f1_friendly: bool | None = Query(None),
    job_type: str | None = Query(None),
    work_mode: str | None = Query(None),
    posted_within: str | None = Query(None),
    match_ids: str | None = Query(None),
) -> JobListResponse:
    query = db.query(Job).filter(Job.is_active == True)  # noqa: E712

    # Track if we need to preserve match_ids order
    preserve_match_order = False
    valid_ids: list[UUID] = []
    
    if match_ids:
        raw_ids = [value.strip() for value in match_ids.split("|") if value.strip()]
        for raw_id in raw_ids:
            try:
                valid_ids.append(UUID(raw_id))
            except ValueError:
                continue
        if valid_ids:
            query = query.filter(Job.id.in_(valid_ids))
            preserve_match_order = True
        else:
            query = query.filter(Job.id == None)  # noqa: E711

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Job.title.ilike(search_term)) |
            (Job.company.ilike(search_term)) |
            (Job.location.ilike(search_term))
        )
    if company:
        # Support multiple companies separated by pipe
        companies = [c.strip() for c in company.split("|")]
        query = query.filter(Job.company.in_(companies))
    if location:
        # Support multiple locations separated by pipe
        # Normalize each location before filtering
        search_locations = [normalize_location(loc.strip()) for loc in location.split("|")]
        search_locations = [loc for loc in search_locations if loc]  # Remove None values
        
        if search_locations:
            # Use ILIKE to match normalized locations (case-insensitive)
            query = query.filter(
                or_(*[Job.location.ilike(f"%{loc}%") for loc in search_locations])
            )
    if category:
        # Support multiple categories separated by pipe
        categories = [c.strip() for c in category.split("|")]
        query = query.filter(Job.job_category.in_(categories))
    if visa_sponsored is not None:
        query = query.filter(Job.visa_sponsored == visa_sponsored)
    if f1_friendly is not None:
        query = query.filter(Job.f1_friendly == f1_friendly)
    if job_type:
        # Filter by job type using pattern matching
        if job_type == "internship":
            query = query.filter(Job.title.ilike("%intern%"))
        elif job_type == "part-time":
            query = query.filter(Job.title.ilike("%part%time%"))
        elif job_type == "full-time":
            query = query.filter(Job.title.ilike("%full%time%"))
    if work_mode:
        # Filter by work mode using pattern matching
        if work_mode == "remote":
            query = query.filter(
                or_(Job.title.ilike("%remote%"), Job.location.ilike("%remote%"))
            )
        elif work_mode == "hybrid":
            query = query.filter(
                or_(Job.title.ilike("%hybrid%"), Job.location.ilike("%hybrid%"))
            )
        elif work_mode == "on-site":
            query = query.filter(
                or_(Job.title.ilike("%on-site%"), Job.location.ilike("%in-office%"))
            )
    
    if posted_within:
        now = datetime.now(timezone.utc)
        if posted_within == "24h":
            cutoff = now - timedelta(hours=24)
        elif posted_within == "week":
            cutoff = now - timedelta(days=7)
        elif posted_within == "month":
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None
        
        if cutoff:
            query = query.filter(Job.posted_at >= cutoff)

    # If we have match_ids, apply custom ordering at SQL level to preserve match ranking
    if preserve_match_order and valid_ids:
        # Build a CASE statement to order by the position in match_ids list
        ordering = case(
            {uid: idx for idx, uid in enumerate(valid_ids)},
            value=Job.id,
            else_=len(valid_ids)
        )
        query = query.order_by(ordering)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return JobListResponse(
        items=[JobResponse.model_validate(job) for job in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/filters/companies")
def get_companies(db: Session = Depends(get_db)) -> list[str]:
    companies = db.query(distinct(Job.company)).filter(Job.is_active == True).order_by(Job.company).all()
    return [c[0] for c in companies]


@router.get("/jobs/filters/locations")
def get_locations(db: Session = Depends(get_db)) -> list[str]:
    locations = db.query(distinct(Job.location)).filter(Job.is_active == True).order_by(Job.location).all()
    return [loc[0] for loc in locations if loc[0]]


@router.get("/jobs/filters/categories")
def get_categories(db: Session = Depends(get_db)) -> list[str]:
    categories = db.query(distinct(Job.job_category)).filter(Job.is_active == True, Job.job_category != None).order_by(Job.job_category).all()
    return [cat[0] for cat in categories if cat[0]]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, db: Session = Depends(get_db)) -> JobResponse:
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()  # noqa: E712
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)
