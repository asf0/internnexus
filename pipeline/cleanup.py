"""Location cleanup module - normalize city/state/country fields."""

from __future__ import annotations

import csv
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db import AsyncSessionLocal
from backend.app.models import (
    Job,
    AshbyJobMetadata,
    GreenhouseJobMetadata,
    LeverJobMetadata,
    JobSource,
)
from pipeline.location.simple_parser import (
    normalize_location,
    normalize_state_name,
    clean_city_name,
    _STATE_NAME_MAPPINGS,
)

logger = logging.getLogger(__name__)

# Patterns that indicate plain "Remote" without country
PLAIN_REMOTE_PATTERNS = [
    r"^remote$",
    r"^work from home$",
    r"^wfh$",
    r"^distributed$",
    r"^virtual$",
    r"^telecommute$",
    r"^anywhere$",
]


def _is_plain_remote(location: str) -> bool:
    """Check if location is plain Remote without explicit country."""
    loc_lower = location.lower().strip()
    for pattern in PLAIN_REMOTE_PATTERNS:
        if re.match(pattern, loc_lower, re.IGNORECASE):
            return True
    return False


def _normalize_for_comparison(value: str | None) -> str:
    """Normalize a string for comparison (lowercase, remove punctuation, extra spaces)."""
    if not value:
        return ""
    # Remove punctuation, normalize whitespace, lowercase
    normalized = re.sub(r"[^\w\s]", "", value.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _contains_normalized(haystack: str, needle: str) -> bool:
    """Check if needle is contained in haystack (both normalized)."""
    haystack_norm = _normalize_for_comparison(haystack)
    needle_norm = _normalize_for_comparison(needle)
    return needle_norm in haystack_norm


def _is_metadata_consistent(
    location_str: str, parsed_from_location: dict, metadata_result: dict
) -> bool:
    """Check if metadata result is consistent with location string.

    Returns True if metadata should be used, False if it should be rejected.
    """
    # If location is plain "Remote", NEVER accept country from metadata
    if _is_plain_remote(location_str) and metadata_result.get("country"):
        return False

    # If location string has a city, metadata must match that city
    location_city = parsed_from_location.get("city")
    metadata_city = metadata_result.get("city")

    if location_city and metadata_city:
        # Check if metadata city matches location city (case-insensitive, contains)
        if not _contains_normalized(location_str, metadata_city):
            # Metadata city not found in location string - likely wrong
            return False

    # If location string has a country, metadata must match that country
    location_country = parsed_from_location.get("country")
    metadata_country = metadata_result.get("country")

    if location_country and metadata_country:
        if not _contains_normalized(location_str, metadata_country):
            # Check common variations
            country_variations = {
                "united states": ["us", "usa", "united states of america", "america"],
                "united kingdom": ["uk", "britain", "great britain", "england"],
                "canada": ["ca"],
            }
            loc_country_norm = _normalize_for_comparison(location_country)
            meta_country_norm = _normalize_for_comparison(metadata_country)

            # Check if either is a variation of the other
            found_match = False
            for country, variations in country_variations.items():
                if loc_country_norm == country or loc_country_norm in variations:
                    if meta_country_norm == country or meta_country_norm in variations:
                        found_match = True
                        break

            if not found_match and loc_country_norm != meta_country_norm:
                return False

    return True


def _parse_location_only(location: str) -> dict:
    """Parse location string into city/state/country without metadata."""
    result = normalize_location(location)
    return {
        "city": result.get("city"),
        "state": result.get("state"),
        "country": result.get("country"),
    }


async def cleanup_locations(
    session: AsyncSession | None = None,
    since: datetime | None = None,
    process_all: bool = False,
    test_mode: bool = False,
    limit: int | None = None,
) -> int:
    """Normalize location data for jobs using batch processing.

    Args:
        session: Database session. If None, creates a new session.
        since: Only process jobs updated since this timestamp. If None, processes all active jobs.
        process_all: If True, re-process all active jobs with locations. If False and no since,
                     only processes jobs that haven't been normalized yet.
        test_mode: If True, write results to CSV without committing changes to database.
        limit: Maximum number of jobs to process (useful for testing).

    Returns:
        Number of jobs updated
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Cleaning up locations...")
    logger.info("=" * 60)

    if test_mode:
        logger.info("TEST MODE: Writing results to CSV (no database changes)")

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        # First, normalize existing states (fix countries stored as states)
        states_fixed = await _normalize_existing_states(session)
        if states_fixed > 0:
            logger.info(f"Fixed {states_fixed} states that were actually countries")

        if since:
            logger.info(f"Processing jobs updated since {since}")
        elif process_all:
            logger.info("Processing ALL active jobs with locations")
        else:
            logger.info("Processing jobs that have not been normalized yet")

        if test_mode:
            return await _process_test_mode_chunked(session, since, process_all, limit)

        return await _process_production_mode_chunked(session, since, process_all, limit)
    finally:
        if should_close_session:
            await session.close()


async def _normalize_existing_states(session: AsyncSession) -> int:
    """Fix states that are actually country names - move to country column."""
    countries_as_states = {
        "Singapore": "Singapore",
        "China": "China",
        "United Kingdom": "United Kingdom",
        "UK": "United Kingdom",
        "Hong Kong": "Hong Kong",
        "India": "India",
        "Ireland": "Ireland",
        "Mexico": "Mexico",
        "South Korea": "South Korea",
        "Korea": "South Korea",
        "Croatia": "Croatia",
        "Japan": "Japan",
        "United States": "United States",
        "US": "United States",
        "Vietnam": "Vietnam",
        "Australia": "Australia",
        "Israel": "Israel",
        "Taiwan": "Taiwan",
        "Germany": "Germany",
        "Netherlands": "Netherlands",
        "Kuwait": "Kuwait",
        "France": "France",
        "Argentina": "Argentina",
        "Romania": "Romania",
        "Brazil": "Brazil",
        "Colombia": "Colombia",
        "Indonesia": "Indonesia",
        "Portugal": "Portugal",
        "Saudi Arabia": "Saudi Arabia",
        "Switzerland": "Switzerland",
        "Bolivia": "Bolivia",
        "Kazakhstan": "Kazakhstan",
        "UAE": "United Arab Emirates",
        "Thailand": "Thailand",
        "Bosnia and Herzegovina": "Bosnia and Herzegovina",
        "Norway": "Norway",
        "Sweden": "Sweden",
        "Denmark": "Denmark",
        "Finland": "Finland",
        "Poland": "Poland",
        "Austria": "Austria",
        "Czechia": "Czechia",
        "Czech Republic": "Czechia",
        "Hungary": "Hungary",
        "Greece": "Greece",
        "Philippines": "Philippines",
        "Malaysia": "Malaysia",
        "New Zealand": "New Zealand",
        "South Africa": "South Africa",
        "Nigeria": "Nigeria",
        "Kenya": "Kenya",
        "Egypt": "Egypt",
        "Turkey": "Turkey",
        "Pakistan": "Pakistan",
        "Bangladesh": "Bangladesh",
        "Chile": "Chile",
        "Peru": "Peru",
        "Ecuador": "Ecuador",
        "Venezuela": "Venezuela",
        "Canada": "Canada",
        "England": "United Kingdom",
        "Scotland": "United Kingdom",
        "Wales": "United Kingdom",
        "Northern Ireland": "United Kingdom",
    }

    cities_as_states = [
        "Oslo",
        "Brussels",
        "Brussels-Capital Region",
        "Budapest",
        "Athens",
        "Copenhagen",
        "Helsinki",
        "Lisbon",
        "Prague",
        "Vienna",
        "Warsaw",
        "Dublin",
        "Rome",
        "Milan",
        "Barcelona",
        "Madrid",
        "Valencia",
        "Munich",
        "Hamburg",
        "Frankfurt",
        "Berlin",
        "Cologne",
        "Stuttgart",
        "Zurich",
        "Geneva",
        "Bern",
        "Basel",
        "Lausanne",
        "Lugano",
        "Vaud",
        "Zug",
        "Stockholm",
        "Gothenburg",
        "Malmo",
        "Amsterdam",
        "Rotterdam",
        "The Hague",
        "Utrecht",
        "Paris",
        "Lyon",
        "Marseille",
        "Toulouse",
        "Nice",
        "Bordeaux",
        "Krakow",
        "Gdansk",
        "Wroclaw",
        "Bratislava",
        "Ljubljana",
        "Zagreb",
        "Grad Zagreb",
        "Sofia",
        "Bucharest",
        "Cluj",
        "Graz",
        "Salzburg",
        "Riga",
        "Vilnius",
        "Tallinn",
        "Harjumaa",
        "Uusimaa",
        "Kyiv",
        "Kyiv City",
        "Lviv",
        "Belgrade",
        "Sarajevo",
        "Skopje",
        "Tirana",
        "London",
        "Greater London",
        "London, City of",
        "London, United Kingdom",
        "Manchester",
        "Leeds",
        "Glasgow",
        "Edinburgh",
        "Liverpool",
        "Sheffield",
        "Bristol",
        "Bristol, City of",
        "Newham",
        "Ealing",
        "Camden",
        "Hampshire",
        "Gloucestershire",
        "Berkshire",
        "Middlesex",
        "Southwark",
        "Hammersmith and Fulham",
        "Midlothian",
        "Abu Dhabi",
        "Dubai",
        "Riyadh",
        "Jeddah",
        "Doha",
        "Kuwait City",
        "Tel Aviv",
        "Jerusalem",
        "Haifa",
        "Central District",
        "Gush Dan",
        "Tehran",
        "Baku",
        "Tbilisi",
        "Yerevan",
        "Cairo",
        "Cairo Governorate",
        "Giza",
        "Istanbul",
        "Ankara",
        "Marmara",
        "Seoul",
        "Busan",
        "Incheon",
        "Gangnam",
        "Gyeonggi Province",
        "Tokyo",
        "Osaka",
        "Fukuoka",
        "Kanto",
        "Kyoto",
        "Nagoya",
        "Yokohama",
        "Beijing",
        "Shanghai",
        "Shanghai Shi",
        "Shenzhen",
        "Hangzhou",
        "Guangzhou",
        "Chengdu",
        "Hong Kong",
        "Singapore",
        "Taipei",
        "Kaohsiung",
        "Hanoi",
        "Ho Chi Minh City",
        "Ha Noi",
        "Bangkok",
        "Phuket",
        "Kuala Lumpur",
        "Penang",
        "Jakarta",
        "Surabaya",
        "Bali",
        "East Java",
        "South Sulawesi",
        "Manila",
        "Cebu",
        "Metro Manila",
        "Manilla",
        "National Capital Region",
        "National Capital Region (Manila)",
        "Mumbai",
        "Delhi",
        "New Delhi",
        "Bangalore",
        "Bengaluru",
        "Chennai",
        "Hyderabad",
        "Pune",
        "Kolkata",
        "Ahmedabad",
        "Jaipur",
        "Gurgaon",
        "Noida",
        "Gujarat",
        "Assam",
        "Kerala",
        "Tamil Nadu",
        "Lagos",
        "Nairobi",
        "Nairobi Area",
        "Johannesburg",
        "Cape Town",
        "Pretoria",
        "Harare",
        "Bujumbura Mairie",
        "Sydney",
        "Melbourne",
        "Brisbane",
        "Perth",
        "Adelaide",
        "Canberra",
        "Auckland",
        "Santiago",
        "Buenos Aires",
        "Lima",
        "Bogota",
        "Caracas",
        "Carabobo",
        "Magdalena",
        "Brasilia",
        "Salvador",
        "Belo Horizonte",
        "La Libertad",
        "Arequipa",
        "Lima Province",
        "Biobio",
        "Arica Y Parinacota",
        "Mexico City",
        "Ciudad de Mexico",
        "Guadalajara",
        "Monterrey",
        "Nuevo Leon",
        "Jalisco",
        "Sonora",
        "Chihuahua",
        "Baja California",
        "Toronto",
        "Vancouver",
        "Montreal",
        "Calgary",
        "Ottawa",
        "Edmonton",
        "Winnipeg",
        "Quebec City",
        "Boston",
        "Chicago",
        "Miami",
        "Seattle",
        "Denver",
        "Atlanta",
        "Dallas",
        "Houston",
        "Phoenix",
        "San Diego",
        "San Jose",
        "San Francisco",
        "Austin",
        "Nashville",
        "Portland",
        "Las Vegas",
        "Baltimore",
        "Minneapolis",
        "Detroit",
        "Cleveland",
        "St. Louis",
        "Kansas City",
        "New Orleans",
        "Orlando",
        "Tampa",
        "Charlotte",
        "Raleigh",
        "Pittsburgh",
        "Columbus",
        "Indianapolis",
        "Milwaukee",
        "Sacramento",
        "San Antonio",
        "Fort Worth",
        "Jacksonville",
        "Louisville",
        "Birmingham",
        "Moscow",
    ]

    invalid_states = [
        "United States & Canada",
        "United States Minor Outlying Islands",
        "EU",
        "Europe",
        "Remote",
        "Hybrid",
        "Any",
        "Various",
        "Multiple",
        "TBD",
        "N/A",
        "FORA, Albert House, 256-260 Old Street, London, EC1V 9DD",
        "Kleine-Gartmanplantsoen 21, 1017RP, Amsterdam",
        "Gangnam",
        "Orchard Road",
    ]

    countries_as_cities = [
        "Afghanistan",
        "Albania",
        "Algeria",
        "Andorra",
        "Angola",
        "Argentina",
        "Armenia",
        "Australia",
        "Austria",
        "Azerbaijan",
        "Bahrain",
        "Bangladesh",
        "Belarus",
        "Belgium",
        "Belize",
        "Benin",
        "Bhutan",
        "Bolivia",
        "Bosnia and Herzegovina",
        "Botswana",
        "Brazil",
        "Brunei",
        "Bulgaria",
        "Burkina Faso",
        "Burundi",
        "Cambodia",
        "Cameroon",
        "Canada",
        "Cape Verde",
        "Central African Republic",
        "Chad",
        "Chile",
        "China",
        "Colombia",
        "Comoros",
        "Congo",
        "Costa Rica",
        "Croatia",
        "Cuba",
        "Cyprus",
        "Czech Republic",
        "Czechia",
        "Denmark",
        "Djibouti",
        "Dominica",
        "Dominican Republic",
        "Ecuador",
        "Egypt",
        "El Salvador",
        "Equatorial Guinea",
        "Eritrea",
        "Estonia",
        "Eswatini",
        "Ethiopia",
        "Fiji",
        "Finland",
        "France",
        "Gabon",
        "Gambia",
        "Georgia",
        "Germany",
        "Ghana",
        "Greece",
        "Grenada",
        "Guatemala",
        "Guinea",
        "Guinea-Bissau",
        "Guyana",
        "Haiti",
        "Honduras",
        "Hungary",
        "Iceland",
        "India",
        "Indonesia",
        "Iran",
        "Iraq",
        "Ireland",
        "Israel",
        "Italy",
        "Jamaica",
        "Japan",
        "Jordan",
        "Kazakhstan",
        "Kenya",
        "Kiribati",
        "Kosovo",
        "Kuwait",
        "Kyrgyzstan",
        "Laos",
        "Latvia",
        "Lebanon",
        "Lesotho",
        "Liberia",
        "Libya",
        "Liechtenstein",
        "Lithuania",
        "Luxembourg",
        "Macedonia",
        "Madagascar",
        "Malawi",
        "Malaysia",
        "Maldives",
        "Mali",
        "Malta",
        "Marshall Islands",
        "Mauritania",
        "Mauritius",
        "Mexico",
        "Micronesia",
        "Moldova",
        "Monaco",
        "Mongolia",
        "Montenegro",
        "Morocco",
        "Mozambique",
        "Myanmar",
        "Namibia",
        "Nauru",
        "Nepal",
        "Netherlands",
        "New Zealand",
        "Nicaragua",
        "Niger",
        "Nigeria",
        "North Korea",
        "North Macedonia",
        "Norway",
        "Oman",
        "Pakistan",
        "Palau",
        "Palestine",
        "Panama",
        "Papua New Guinea",
        "Paraguay",
        "Peru",
        "Philippines",
        "Poland",
        "Portugal",
        "Qatar",
        "Romania",
        "Russia",
        "Rwanda",
        "Saint Kitts and Nevis",
        "Saint Lucia",
        "Saint Vincent and the Grenadines",
        "Samoa",
        "San Marino",
        "Sao Tome and Principe",
        "Saudi Arabia",
        "Senegal",
        "Serbia",
        "Seychelles",
        "Sierra Leone",
        "Singapore",
        "Slovakia",
        "Slovenia",
        "Solomon Islands",
        "Somalia",
        "South Africa",
        "South Korea",
        "South Sudan",
        "Spain",
        "Sri Lanka",
        "Sudan",
        "Suriname",
        "Swaziland",
        "Sweden",
        "Switzerland",
        "Syria",
        "Taiwan",
        "Tajikistan",
        "Tanzania",
        "Thailand",
        "Timor-Leste",
        "Togo",
        "Tonga",
        "Trinidad and Tobago",
        "Tunisia",
        "Turkey",
        "Turkmenistan",
        "Tuvalu",
        "Uganda",
        "Ukraine",
        "United Arab Emirates",
        "UAE",
        "United Kingdom",
        "UK",
        "United States",
        "US",
        "USA",
        "Uruguay",
        "Uzbekistan",
        "Vanuatu",
        "Vatican City",
        "Venezuela",
        "Vietnam",
        "Yemen",
        "Zambia",
        "Zimbabwe",
        "Africa",
        "Asia",
        "Europe",
        "North America",
        "South America",
        "Oceania",
        "Latin America",
        "Central America",
        "Caribbean",
        "Middle East",
        "European Union",
        "Americas",
    ]

    states_as_cities = [
        "Alabama",
        "Alaska",
        "Arizona",
        "Arkansas",
        "California",
        "Colorado",
        "Connecticut",
        "Delaware",
        "Florida",
        "Georgia",
        "Hawaii",
        "Idaho",
        "Illinois",
        "Indiana",
        "Iowa",
        "Kansas",
        "Kentucky",
        "Louisiana",
        "Maine",
        "Maryland",
        "Massachusetts",
        "Michigan",
        "Minnesota",
        "Mississippi",
        "Missouri",
        "Montana",
        "Nebraska",
        "Nevada",
        "New Hampshire",
        "New Jersey",
        "New Mexico",
        "New York",
        "North Carolina",
        "North Dakota",
        "Ohio",
        "Oklahoma",
        "Oregon",
        "Pennsylvania",
        "Rhode Island",
        "South Carolina",
        "South Dakota",
        "Tennessee",
        "Texas",
        "Utah",
        "Vermont",
        "Virginia",
        "Washington",
        "West Virginia",
        "Wisconsin",
        "Wyoming",
        "District of Columbia",
        "Puerto Rico",
        "Alberta",
        "British Columbia",
        "Manitoba",
        "New Brunswick",
        "Newfoundland and Labrador",
        "Nova Scotia",
        "Ontario",
        "Prince Edward Island",
        "Quebec",
        "Saskatchewan",
        "Yukon",
        "Northwest Territories",
        "Nunavut",
        "England",
        "Scotland",
        "Wales",
        "Northern Ireland",
        "Andhra Pradesh",
        "Arunachal Pradesh",
        "Assam",
        "Bihar",
        "Chhattisgarh",
        "Goa",
        "Gujarat",
        "Haryana",
        "Himachal Pradesh",
        "Jharkhand",
        "Karnataka",
        "Kerala",
        "Madhya Pradesh",
        "Maharashtra",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Odisha",
        "Punjab",
        "Rajasthan",
        "Sikkim",
        "Tamil Nadu",
        "Telangana",
        "Tripura",
        "Uttar Pradesh",
        "Uttarakhand",
        "West Bengal",
        "Delhi",
        "New South Wales",
        "Victoria",
        "Queensland",
        "South Australia",
        "Western Australia",
        "Tasmania",
        "Australian Capital Territory",
        "Northern Territory",
        "Bavaria",
        "Baden-Wurttemberg",
        "Brandenburg",
        "Hesse",
        "Lower Saxony",
        "Mecklenburg-Vorpommern",
        "North Rhine-Westphalia",
        "Rhineland-Palatinate",
        "Saarland",
        "Saxony",
        "Saxony-Anhalt",
        "Schleswig-Holstein",
        "Thuringia",
        "Flanders",
        "Wallonia",
        "Catalonia",
        "Basque Country",
        "Galicia",
        "Andalusia",
        "Ile-de-France",
        "Brittany",
        "Normandy",
        "Provence-Alpes-Cote d'Azur",
        "Occitanie",
        "Hauts-de-France",
        "Grand Est",
        "Pays de la Loire",
        "Auvergne-Rhone-Alpes",
        "Lombardy",
        "Lazio",
        "Campania",
        "Sicily",
        "Veneto",
        "Emilia-Romagna",
        "Piedmont",
        "Tuscany",
        "Apulia",
        "Calabria",
        "Sardinia",
        "Liguria",
        "Marche",
        "Abruzzo",
        "Umbria",
        "Friuli-Venezia Giulia",
        "Trentino-Alto Adige",
        "Molise",
        "Basilicata",
    ]

    invalid_city_patterns = [
        "^All ",
        "^Flex[- ]",
        "^Home[-:\\s]",
        " or ",
        "^\\d+\\s",
        "^Across ",
        "^Any",
        "^Beyond ",
        "^[a-zA-Z]$",
        "^Contract",
        "^Hybrid$",
        "^Central ",
        "^LT -",
        "^Greater ",
    ]

    total_updated = 0

    await session.execute(text("UPDATE jobs SET state = TRIM(state) WHERE state IS NOT NULL"))
    await session.execute(text("UPDATE jobs SET city = TRIM(city) WHERE city IS NOT NULL"))
    await session.execute(text("UPDATE jobs SET country = TRIM(country) WHERE country IS NOT NULL"))

    state_keys = list(countries_as_states.keys())
    case_clauses = " WHEN ".join(
        f"state = '{state}' THEN '{country}'" for state, country in countries_as_states.items()
    )
    case_clauses = f"CASE WHEN {case_clauses} END"
    result = await session.execute(
        text(f"""
            UPDATE jobs SET country = {case_clauses}, state = NULL
            WHERE state = ANY(:states)
        """),
        {"states": state_keys},
    )
    total_updated += result.rowcount or 0

    result = await session.execute(
        text("UPDATE jobs SET state = NULL WHERE state = ANY(:cities)"),
        {"cities": cities_as_states},
    )
    total_updated += result.rowcount or 0

    result = await session.execute(
        text("UPDATE jobs SET state = NULL WHERE state = ANY(:invalid)"),
        {"invalid": invalid_states},
    )
    total_updated += result.rowcount or 0

    state_mappings_with_values = {k: v for k, v in _STATE_NAME_MAPPINGS.items() if v is not None}
    state_mappings_null = [k for k, v in _STATE_NAME_MAPPINGS.items() if v is None]

    if state_mappings_with_values:
        case_clauses = " WHEN ".join(
            f"state = '{state}' THEN '{new_state}'"
            for state, new_state in state_mappings_with_values.items()
        )
        case_clauses = f"CASE WHEN {case_clauses} END"
        result = await session.execute(
            text(f"""
                UPDATE jobs SET state = {case_clauses}
                WHERE state = ANY(:old_states)
            """),
            {"old_states": list(state_mappings_with_values.keys())},
        )
        total_updated += result.rowcount or 0

    if state_mappings_null:
        result = await session.execute(
            text("UPDATE jobs SET state = NULL WHERE state = ANY(:null_states)"),
            {"null_states": state_mappings_null},
        )
        total_updated += result.rowcount or 0

    lower_countries = [c.lower() for c in countries_as_cities]
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE LOWER(city) = ANY(:countries)"),
        {"countries": lower_countries},
    )
    total_updated += result.rowcount or 0

    lower_states = [s.lower() for s in states_as_cities]
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE LOWER(city) = ANY(:states)"),
        {"states": lower_states},
    )
    total_updated += result.rowcount or 0

    combined_pattern = "|".join(invalid_city_patterns)
    result = await session.execute(
        text("UPDATE jobs SET city = NULL WHERE city ~* :pattern"),
        {"pattern": combined_pattern},
    )
    total_updated += result.rowcount or 0

    await session.commit()
    return total_updated


async def _get_total_count(session: AsyncSession, since, process_all) -> int:
    """Get total count of jobs to process."""
    if since:
        stmt = (
            select(func.count())
            .select_from(Job)
            .where(Job.is_active == True, Job.last_seen >= since, Job.location.isnot(None))
        )
    elif process_all:
        stmt = (
            select(func.count())
            .select_from(Job)
            .where(Job.is_active == True, Job.location.isnot(None))
        )
    else:
        stmt = (
            select(func.count())
            .select_from(Job)
            .where(
                Job.is_active == True,
                Job.location.isnot(None),
                Job.city.is_(None),
                Job.state.is_(None),
                Job.country.is_(None),
            )
        )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def _fetch_jobs_chunk(
    session: AsyncSession, since, process_all, offset: int, chunk_size: int
):
    """Fetch a chunk of jobs with only needed columns, including source metadata."""
    if since:
        stmt = (
            select(Job.id, Job.source, Job.location, Job.city, Job.state, Job.country)
            .where(Job.is_active == True, Job.last_seen >= since, Job.location.isnot(None))
            .offset(offset)
            .limit(chunk_size)
        )
    elif process_all:
        stmt = (
            select(Job.id, Job.source, Job.location, Job.city, Job.state, Job.country)
            .where(Job.is_active == True, Job.location.isnot(None))
            .offset(offset)
            .limit(chunk_size)
        )
    else:
        stmt = (
            select(Job.id, Job.source, Job.location, Job.city, Job.state, Job.country)
            .where(
                Job.is_active == True,
                Job.location.isnot(None),
                Job.city.is_(None),
                Job.state.is_(None),
                Job.country.is_(None),
            )
            .offset(offset)
            .limit(chunk_size)
        )
    result = await session.execute(stmt)
    jobs = result.mappings().all()

    job_ids = [job.id for job in jobs]
    if not job_ids:
        return jobs, {}, {}, {}

    # Fetch Ashby metadata
    ashby_stmt = select(
        AshbyJobMetadata.job_id,
        AshbyJobMetadata.address_locality,
        AshbyJobMetadata.address_region,
        AshbyJobMetadata.address_country,
    ).where(AshbyJobMetadata.job_id.in_(job_ids))
    ashby_result = await session.execute(ashby_stmt)
    ashby_map = {row.job_id: row for row in ashby_result.all()}

    # Fetch Greenhouse metadata
    greenhouse_stmt = select(
        GreenhouseJobMetadata.job_id,
        GreenhouseJobMetadata.offices,
    ).where(GreenhouseJobMetadata.job_id.in_(job_ids))
    greenhouse_result = await session.execute(greenhouse_stmt)
    greenhouse_map = {row.job_id: row for row in greenhouse_result.all()}

    # Fetch Lever metadata
    lever_stmt = select(
        LeverJobMetadata.job_id,
        LeverJobMetadata.all_locations,
    ).where(LeverJobMetadata.job_id.in_(job_ids))
    lever_result = await session.execute(lever_stmt)
    lever_map = {row.job_id: row for row in lever_result.all()}

    return jobs, ashby_map, greenhouse_map, lever_map


def _get_metadata_result(
    row, ashby_map: dict, greenhouse_map: dict, lever_map: dict
) -> tuple[dict | None, str]:
    """Try to get location data from metadata. Returns (result, source) or (None, '')."""

    # For Ashby jobs, use metadata address if available
    if row.source == JobSource.ashby and row.id in ashby_map:
        ashby = ashby_map[row.id]
        if ashby.address_locality and ashby.address_region and ashby.address_country:
            addr_country = ashby.address_country
            if addr_country.upper() == "USA":
                addr_country = "United States"
            raw_location = f"{ashby.address_locality}, {ashby.address_region}, {addr_country}"
            parsed = normalize_location(raw_location)
            raw_state = parsed.get("state") or ashby.address_region
            normalized_state = normalize_state_name(raw_state) if raw_state else None
            raw_city = parsed.get("city") or ashby.address_locality
            normalized_city = clean_city_name(raw_city) if raw_city else None
            return {
                "city": normalized_city,
                "state": normalized_state,
                "country": parsed.get("country") or addr_country,
            }, "ashby_metadata"

    # For Greenhouse jobs, use offices metadata if available
    if row.source == JobSource.greenhouse and row.id in greenhouse_map:
        gh = greenhouse_map[row.id]
        offices = gh.offices or []
        for office in offices:
            office_loc = office.get("location")
            office_name = office.get("name", "").strip()

            # If location is null, try using office name as fallback
            if not office_loc or not office_loc.strip():
                skip_patterns = (
                    "US",
                    "UK",
                    "EU",
                    "APAC",
                    "EMEA",
                    "North America",
                    "South America",
                    "Canada Locations",
                    "LT - North America",
                )
                if office_name.upper() in skip_patterns:
                    continue
                if "remote" in office_name.lower():
                    office_loc = office_name
                elif len(office_name) > 2 and "," not in office_name and len(office_name) < 30:
                    office_loc = office_name

            if office_loc and office_loc.strip():
                parsed = normalize_location(office_loc)
                if parsed.get("city") or parsed.get("country") or parsed.get("full") == "Remote":
                    raw_state = parsed.get("state")
                    normalized_state = normalize_state_name(raw_state) if raw_state else None
                    raw_city = parsed.get("city")
                    normalized_city = clean_city_name(raw_city) if raw_city else None
                    return {
                        "city": normalized_city,
                        "state": normalized_state,
                        "country": parsed.get("country"),
                    }, "greenhouse_metadata"

    # For Lever jobs, use all_locations metadata if available
    if row.source == JobSource.lever and row.id in lever_map:
        lev = lever_map[row.id]
        all_locs = lev.all_locations or []
        if all_locs and all_locs[0]:
            parsed = normalize_location(all_locs[0])
            if parsed.get("city") or parsed.get("country"):
                raw_state = parsed.get("state")
                normalized_state = normalize_state_name(raw_state) if raw_state else None
                raw_city = parsed.get("city")
                normalized_city = clean_city_name(raw_city) if raw_city else None
                return {
                    "city": normalized_city,
                    "state": normalized_state,
                    "country": parsed.get("country"),
                }, "lever_metadata"

    return None, "fallback"


def _merge_location_results(
    location_str: str, parsed_result: dict, metadata_result: dict | None, metadata_source: str
) -> tuple[dict, str]:
    """Merge parsed location with metadata, validating consistency.

    Returns (merged_result, source_used).
    """
    # If location is plain Remote, NEVER use metadata country
    if _is_plain_remote(location_str):
        return {
            "city": None,
            "state": None,
            "country": None,
        }, "location_string"

    # If we have a good parsed result, use it
    if parsed_result.get("city") or parsed_result.get("country"):
        # Check if metadata is consistent and can add missing info
        if metadata_result and _is_metadata_consistent(
            location_str, parsed_result, metadata_result
        ):
            # Use metadata to fill in missing fields only
            # But normalize the state to filter out cities/countries in state field
            raw_state = parsed_result.get("state") or metadata_result.get("state")
            normalized_state = normalize_state_name(raw_state) if raw_state else None
            merged = {
                "city": parsed_result.get("city") or metadata_result.get("city"),
                "state": normalized_state,
                "country": parsed_result.get("country") or metadata_result.get("country"),
            }
            return merged, metadata_source

        return parsed_result, "location_string"

    # If parsed result is incomplete, try metadata
    if metadata_result and _is_metadata_consistent(location_str, parsed_result, metadata_result):
        # Normalize state in metadata result too
        raw_state = metadata_result.get("state")
        if raw_state:
            metadata_result = {
                **metadata_result,
                "state": normalize_state_name(raw_state),
            }
        return metadata_result, metadata_source

    # Fall back to parsed result (even if incomplete)
    return parsed_result, "location_string"


async def _process_production_mode_chunked(
    session: AsyncSession, since, process_all, limit: int | None
) -> int:
    """Process jobs in production mode using chunked queries."""
    unique_locations: dict[str, dict] = {}
    total_processed = 0
    total_updated = 0
    chunk_size = 5000  # Increased from 1000 for better bulk update performance

    total_count = await _get_total_count(session, since, process_all)
    logger.info(f"Found {total_count} jobs to process")

    logger.info("Building unique location cache and applying changes...")

    offset = 0
    while True:
        if limit and total_processed >= limit:
            break

        rows, ashby_map, greenhouse_map, lever_map = await _fetch_jobs_chunk(
            session, since, process_all, offset, chunk_size
        )
        if not rows:
            break

        offset += len(rows)
        batch_updates = []

        for row in rows:
            if limit and total_processed >= limit:
                break

            total_processed += 1
            location = row.location

            if not location:
                continue

            # STEP 1: Parse location string first (what candidates actually see)
            if location not in unique_locations:
                unique_locations[location] = _parse_location_only(location)
                if len(unique_locations) % 500 == 0:
                    logger.info(f"Normalized {len(unique_locations)} unique locations...")

            parsed_result = unique_locations[location]

            # Normalize state name to fix variations (DC, accents, etc.)
            if parsed_result.get("state"):
                parsed_result["state"] = normalize_state_name(parsed_result["state"])

            # STEP 2: Try to get metadata (but don't use it yet)
            metadata_result, metadata_source = _get_metadata_result(
                row, ashby_map, greenhouse_map, lever_map
            )

            # STEP 3: Merge results with validation
            final_result, source_used = _merge_location_results(
                location, parsed_result, metadata_result, metadata_source
            )

            # STEP 4: Check if anything changed (city/state/country only)
            changed = (
                final_result["city"] != row.city
                or final_result["state"] != row.state
                or final_result["country"] != row.country
            )

            if changed:
                # IMPORTANT: Only update city, state, country - preserve original location
                batch_updates.append(
                    {
                        "id": row.id,
                        "city": final_result["city"],
                        "state": final_result["state"],
                        "country": final_result["country"],
                    }
                )

        if batch_updates:
            await _apply_batch_updates(session, batch_updates)
            total_updated += len(batch_updates)

        if total_processed % 5000 == 0:
            logger.info(
                f"Processed {total_processed}/{min(total_count, limit or total_count)} jobs..."
            )

    logger.info(f"Normalized {len(unique_locations)} unique locations")
    logger.info(f"Processed {total_processed} jobs, updated {total_updated}")
    return total_updated


async def _apply_batch_updates(session: AsyncSession, updates: list[dict]) -> None:
    """Apply batch updates to jobs using SQLAlchemy 2.0 bulk update.

    Uses bulk_update_mappings for optimal performance - reduces 1,000 individual
    UPDATE statements to a single bulk operation per chunk.

    Args:
        session: Database session
        updates: List of dicts with 'id', 'city', 'state', 'country' keys
    """
    if not updates:
        return

    from sqlalchemy import update

    # SQLAlchemy 2.0 bulk update - single operation for all records
    # This performs: UPDATE jobs SET city=..., state=..., country=... WHERE id IN (...)
    # using CASE expressions internally for optimal performance
    await session.execute(update(Job), updates, execution_options={"synchronize_session": False})
    await session.commit()


async def _process_test_mode_chunked(
    session: AsyncSession, since, process_all, limit: int | None
) -> int:
    """Process jobs in test mode using chunked queries."""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    csv_path = output_dir / "location_test_results.csv"

    unique_locations: dict[str, dict] = {}
    total_processed = 0
    chunk_size = 5000  # Increased from 1000 for consistency

    total_count = await _get_total_count(session, since, process_all)
    logger.info(f"Found {total_count} jobs to process")

    logger.info("Building unique location cache and writing to CSV...")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "source",
                "original_location",
                "city",
                "state",
                "country",
                "fix_source",
            ],
        )
        writer.writeheader()

        offset = 0
        while True:
            if limit and total_processed >= limit:
                break

            rows, ashby_map, greenhouse_map, lever_map = await _fetch_jobs_chunk(
                session, since, process_all, offset, chunk_size
            )
            if not rows:
                break

            offset += len(rows)
            batch_results = []

            for row in rows:
                if limit and total_processed >= limit:
                    break

                total_processed += 1
                location = row.location

                if not location:
                    continue

                # STEP 1: Parse location string first
                if location not in unique_locations:
                    unique_locations[location] = _parse_location_only(location)
                    if len(unique_locations) % 500 == 0:
                        logger.info(f"Normalized {len(unique_locations)} unique locations...")

                parsed_result = unique_locations[location]

                # Normalize state name to fix variations (DC, accents, etc.)
                if parsed_result.get("state"):
                    parsed_result["state"] = normalize_state_name(parsed_result["state"])

                # STEP 2: Try to get metadata
                metadata_result, metadata_source = _get_metadata_result(
                    row, ashby_map, greenhouse_map, lever_map
                )

                # STEP 3: Merge results with validation
                final_result, source_used = _merge_location_results(
                    location, parsed_result, metadata_result, metadata_source
                )

                batch_results.append(
                    {
                        "id": str(row.id),
                        "source": row.source.value
                        if hasattr(row.source, "value")
                        else str(row.source),
                        "original_location": location or "",
                        "city": final_result["city"] or "",
                        "state": final_result["state"] or "",
                        "country": final_result["country"] or "",
                        "fix_source": source_used,
                    }
                )

            if batch_results:
                writer.writerows(batch_results)

            if total_processed % 5000 == 0:
                logger.info(
                    f"Processed {total_processed}/{min(total_count, limit or total_count)} jobs..."
                )

    logger.info(f"Normalized {len(unique_locations)} unique locations")
    logger.info(f"Processed {total_processed} jobs")
    logger.info(f"Results saved to {csv_path}")
    logger.info(f"Step 'cleanup' completed in test mode - no database changes")
    return total_processed


async def delete_old_jobs(session: AsyncSession | None = None, days: int = 7) -> int:
    """
    Permanently delete jobs that haven't been seen in X days.

    Args:
        session: Database session (creates new one if None)
        days: Delete jobs older than this many days (default: 7)

    Returns:
        Number of jobs deleted
    """
    logger.info("=" * 60)
    logger.info(f"STEP: Deleting jobs older than {days} days...")
    logger.info("=" * 60)

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Count before deletion
        result = await session.execute(
            select(func.count()).select_from(Job).where(Job.last_seen < cutoff_date)
        )
        count_to_delete = result.scalar()

        if count_to_delete == 0:
            logger.info("No old jobs to delete")
            return 0

        logger.info(f"Deleting {count_to_delete} jobs older than {days} days")

        # Delete old jobs permanently
        result = await session.execute(delete(Job).where(Job.last_seen < cutoff_date))
        await session.commit()

        deleted_count = result.rowcount
        logger.info(f"Successfully deleted {deleted_count} old jobs")
        return deleted_count

    finally:
        if should_close_session:
            await session.close()


async def delete_inactive_jobs(session: AsyncSession | None = None) -> int:
    """
    Permanently delete jobs marked as inactive (not seen in current API response).

    This is part of the sync model: after marking all jobs inactive and re-ingesting
    from APIs, any jobs that remain inactive were not found in the APIs and should
    be deleted.

    Args:
        session: Database session (creates new one if None)

    Returns:
        Number of jobs deleted
    """
    logger.info("=" * 60)
    logger.info("STEP: Deleting inactive jobs (sync model)...")
    logger.info("=" * 60)

    should_close_session = session is None
    if should_close_session:
        session = AsyncSessionLocal()

    try:
        # Count before deletion
        result = await session.execute(
            select(func.count()).select_from(Job).where(Job.is_active == False)
        )
        count_to_delete = result.scalar()

        if count_to_delete == 0:
            logger.info("No inactive jobs to delete")
            return 0

        logger.info(f"Deleting {count_to_delete} inactive jobs")

        # Delete inactive jobs permanently
        result = await session.execute(delete(Job).where(Job.is_active == False))
        await session.commit()

        deleted_count = result.rowcount
        logger.info(f"Successfully deleted {deleted_count} inactive jobs")
        return deleted_count

    finally:
        if should_close_session:
            await session.close()
