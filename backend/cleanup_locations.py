"""Script to clean up and normalize location data in the database."""
from __future__ import annotations

import re
from sqlalchemy.orm import Session
from app.db import engine
from app.models import Job

# US State abbreviations to full names
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

# Reverse lookup: full name to abbreviation
STATE_NAMES_TO_ABBR = {v.lower(): k for k, v in US_STATES.items()}

# Full state names set for quick lookup
US_STATE_NAMES = set(v.lower() for v in US_STATES.values())

# Country variations to normalized form
COUNTRY_ALIASES = {
    'usa': 'United States',
    'us': 'United States', 
    'u.s.': 'United States',
    'u.s.a.': 'United States',
    'united states': 'United States',
    'united states of america': 'United States',
    'usa hq': 'United States',
    'us hq': 'United States',
    'uk': 'United Kingdom',
    'gb': 'United Kingdom',
    'great britain': 'United Kingdom',
    'england': 'United Kingdom',
    'ca': 'Canada',
    'canada': 'Canada',
    'au': 'Australia',
    'australia': 'Australia',
    'de': 'Germany',
    'germany': 'Germany',
    'fr': 'France',
    'france': 'France',
    'jp': 'Japan',
    'japan': 'Japan',
    'sg': 'Singapore',
    'singapore': 'Singapore',
    'in': 'India',
    'india': 'India',
    'ie': 'Ireland',
    'ireland': 'Ireland',
    'nl': 'Netherlands',
    'netherlands': 'Netherlands',
    'ch': 'Switzerland',
    'switzerland': 'Switzerland',
    'se': 'Sweden',
    'sweden': 'Sweden',
    'il': 'Israel',
    'israel': 'Israel',
    'br': 'Brazil',
    'brazil': 'Brazil',
    'mx': 'Mexico',
    'mexico': 'Mexico',
    'es': 'Spain',
    'spain': 'Spain',
    'it': 'Italy',
    'italy': 'Italy',
    'pl': 'Poland',
    'poland': 'Poland',
    'cn': 'China',
    'china': 'China',
    'hk': 'Hong Kong',
    'hong kong': 'Hong Kong',
    'kr': 'South Korea',
    'south korea': 'South Korea',
    'tw': 'Taiwan',
    'taiwan': 'Taiwan',
    'nz': 'New Zealand',
    'new zealand': 'New Zealand',
}

COUNTRY_NAMES = set(COUNTRY_ALIASES.values())


def normalize_country(text: str) -> str | None:
    """Normalize a country name/abbreviation to standard form."""
    if not text:
        return None
    cleaned = re.sub(r'\s+', ' ', text.strip().lower())
    return COUNTRY_ALIASES.get(cleaned)


def is_us_state(text: str) -> bool:
    """Check if text is a US state name or abbreviation."""
    if not text:
        return False
    cleaned = text.strip().lower()
    return cleaned in US_STATE_NAMES or cleaned.upper() in US_STATES


def normalize_state(text: str) -> str | None:
    """Normalize state to full name."""
    if not text:
        return None
    cleaned = text.strip()
    upper = cleaned.upper()
    if upper in US_STATES:
        return US_STATES[upper]
    lower = cleaned.lower()
    if lower in STATE_NAMES_TO_ABBR:
        return US_STATES[STATE_NAMES_TO_ABBR[lower]]
    return None


def clean_location(location: str) -> dict:
    """
    Parse and normalize a location string into city, state, country.
    
    Returns dict with 'location', 'city', 'state', 'country'
    """
    if not location or not location.strip():
        return {"location": None, "city": None, "state": None, "country": None}
    
    original = location
    location = location.strip()
    
    # Handle Remote
    if location.lower() in ['remote', 'remote work', 'work from home', 'wfh', 'anywhere']:
        return {"location": "Remote", "city": None, "state": None, "country": None}
    
    # Clean up common suffixes
    location = re.sub(r'\s*hq\s*$', '', location, flags=re.IGNORECASE)
    location = re.sub(r'\s*headquarters\s*$', '', location, flags=re.IGNORECASE)
    location = re.sub(r'\s*office\s*$', '', location, flags=re.IGNORECASE)
    
    # Remove parenthetical content
    location = re.sub(r'\([^)]*\)', '', location).strip()
    
    # Split by comma
    parts = [p.strip() for p in location.split(',') if p.strip()]
    
    # If single part with spaces, try to split smartly
    if len(parts) == 1 and ' ' in parts[0]:
        words = parts[0].split()
        # Check if last word is state abbreviation
        if len(words[-1]) == 2 and words[-1].upper() in US_STATES:
            parts = [' '.join(words[:-1]), words[-1]]
    
    city = None
    state = None
    country = None
    
    # Process parts from end to start (country, state, city)
    remaining_parts = []
    
    for part in reversed(parts):
        part_clean = part.strip()
        
        # Check if it's a country
        normalized_country = normalize_country(part_clean)
        if normalized_country and country is None:
            country = normalized_country
            continue
        
        # Check if it's a US state
        normalized_state = normalize_state(part_clean)
        if normalized_state and state is None:
            state = normalized_state
            # If we found a state and no country yet, assume United States
            if country is None:
                country = "United States"
            continue
        
        # Otherwise it's part of city/location name
        remaining_parts.insert(0, part_clean.title())
    
    # Remaining parts form the city
    if remaining_parts:
        city = ', '.join(remaining_parts)
        # Special case: if city is actually a state name (e.g., "Illinois, United States")
        if is_us_state(city) and state is None:
            state = normalize_state(city)
            city = None
    
    # Build normalized location string
    loc_parts = []
    if city:
        loc_parts.append(city)
    if state:
        loc_parts.append(state)
    if country:
        loc_parts.append(country)
    
    normalized_location = ', '.join(loc_parts) if loc_parts else original
    
    return {
        "location": normalized_location,
        "city": city,
        "state": state,
        "country": country
    }


def main():
    """Run the location cleanup."""
    print("Starting location cleanup...")
    
    with Session(engine) as session:
        jobs = session.query(Job).filter(Job.is_active == True).all()
        print(f"Found {len(jobs)} active jobs to process")
        
        updated = 0
        for job in jobs:
            if not job.location:
                continue
            
            result = clean_location(job.location)
            
            # Check if anything changed
            changed = False
            if result["location"] != job.location:
                changed = True
            if result["city"] != job.city:
                changed = True
            if result["state"] != job.state:
                changed = True
            if result["country"] != job.country:
                changed = True
            
            if changed:
                old_loc = f"{job.location} | city={job.city}, state={job.state}, country={job.country}"
                new_loc = f"{result['location']} | city={result['city']}, state={result['state']}, country={result['country']}"
                print(f"  {old_loc}")
                print(f"    -> {new_loc}")
                
                job.location = result["location"]
                job.city = result["city"]
                job.state = result["state"]
                job.country = result["country"]
                updated += 1
        
        print(f"\nUpdated {updated} jobs")
        
        if updated > 0:
            confirm = input("Commit changes? (y/n): ")
            if confirm.lower() == 'y':
                session.commit()
                print("Changes committed!")
            else:
                session.rollback()
                print("Changes rolled back.")


if __name__ == "__main__":
    main()
