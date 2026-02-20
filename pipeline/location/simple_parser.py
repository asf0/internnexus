"""Simple location parser without geostring dependency."""

from __future__ import annotations

import re
from typing import Any

# =============================================================================
# PRE-COMPILED REGEX PATTERNS
# Compiled once at module import for optimal performance (~20-30% speedup)
# =============================================================================

# Street address detection
_STREET_NUMBER_PATTERN = re.compile(r"^\d+\s")

# Fake city detection
_FAKE_CITY_PATTERNS = [
    re.compile(r"\b" + indicator + r"\b", re.IGNORECASE)
    for indicator in [
        "remote",
        "hybrid",
        "zone",
        "region",
        "area",
        "various",
        "multiple",
        "distributed",
        "virtual",
        "anywhere",
        "any",
        "flexible",
        "tbd",
        "n/a",
        "unknown",
        "hub",
        "center",
        "office",
        "location",
        "suite",
        "apt",
        "unit",
        "building",
        "floor",
        "room",
        "plaza",
        "mall",
        "amer",
        "apac",
        "emea",
        "latam",
        "global",
        "eu",
        "europe",
    ]
]
_FAKE_CITY_PREFIX_PATTERN = re.compile(r"^(remote|zone|region)\s+\w+", re.IGNORECASE)

# Countries that should NEVER be in city field
_COUNTRIES_AS_CITIES = {
    "afghanistan",
    "albania",
    "algeria",
    "andorra",
    "angola",
    "antarctica",
    "argentina",
    "armenia",
    "australia",
    "austria",
    "azerbaijan",
    "bahrain",
    "bangladesh",
    "belarus",
    "belgium",
    "belize",
    "benin",
    "bhutan",
    "bolivia",
    "bosnia",
    "bosnia and herzegovina",
    "botswana",
    "brazil",
    "brunei",
    "bulgaria",
    "burkina faso",
    "burundi",
    "cambodia",
    "cameroon",
    "canada",
    "cape verde",
    "central african republic",
    "chad",
    "chile",
    "china",
    "colombia",
    "comoros",
    "congo",
    "costa rica",
    "croatia",
    "cuba",
    "cyprus",
    "czech republic",
    "czechia",
    "denmark",
    "djibouti",
    "dominica",
    "dominican republic",
    "ecuador",
    "egypt",
    "el salvador",
    "equatorial guinea",
    "eritrea",
    "estonia",
    "eswatini",
    "ethiopia",
    "fiji",
    "finland",
    "france",
    "gabon",
    "gambia",
    "georgia",
    "germany",
    "ghana",
    "greece",
    "grenada",
    "guatemala",
    "guinea",
    "guinea-bissau",
    "guyana",
    "haiti",
    "honduras",
    "hungary",
    "iceland",
    "india",
    "indonesia",
    "iran",
    "iraq",
    "ireland",
    "israel",
    "italy",
    "jamaica",
    "japan",
    "jordan",
    "kazakhstan",
    "kenya",
    "kiribati",
    "kosovo",
    "kuwait",
    "kyrgyzstan",
    "laos",
    "latvia",
    "lebanon",
    "lesotho",
    "liberia",
    "libya",
    "liechtenstein",
    "lithuania",
    "luxembourg",
    "macedonia",
    "madagascar",
    "malawi",
    "malaysia",
    "maldives",
    "mali",
    "malta",
    "marshall islands",
    "mauritania",
    "mauritius",
    "mexico",
    "micronesia",
    "moldova",
    "monaco",
    "mongolia",
    "montenegro",
    "morocco",
    "mozambique",
    "myanmar",
    "namibia",
    "nauru",
    "nepal",
    "netherlands",
    "new zealand",
    "nicaragua",
    "niger",
    "nigeria",
    "north korea",
    "korea",
    "north macedonia",
    "norway",
    "oman",
    "pakistan",
    "palau",
    "palestine",
    "panama",
    "papua new guinea",
    "paraguay",
    "peru",
    "philippines",
    "poland",
    "portugal",
    "qatar",
    "romania",
    "russia",
    "rwanda",
    "saint kitts and nevis",
    "saint lucia",
    "saint vincent and the grenadines",
    "samoa",
    "san marino",
    "sao tome and principe",
    "saudi arabia",
    "senegal",
    "serbia",
    "seychelles",
    "sierra leone",
    "singapore",
    "slovakia",
    "slovenia",
    "solomon islands",
    "somalia",
    "south africa",
    "south korea",
    "south sudan",
    "spain",
    "sri lanka",
    "sudan",
    "suriname",
    "swaziland",
    "sweden",
    "switzerland",
    "syria",
    "taiwan",
    "tajikistan",
    "tanzania",
    "thailand",
    "timor-leste",
    "togo",
    "tonga",
    "trinidad and tobago",
    "tunisia",
    "turkey",
    "turkmenistan",
    "tuvalu",
    "uganda",
    "ukraine",
    "united arab emirates",
    "uae",
    "united kingdom",
    "uk",
    "united states",
    "us",
    "usa",
    "uruguay",
    "uzbekistan",
    "vanuatu",
    "vatican city",
    "venezuela",
    "vietnam",
    "yemen",
    "zambia",
    "zimbabwe",
    # Continents/regions
    "africa",
    "asia",
    "europe",
    "north america",
    "south america",
    "oceania",
    "latin america",
    "central america",
    "caribbean",
    "middle east",
    "european union",
    "americas",
}

# States/provinces/regions that should NEVER be in city field
_STATES_AS_CITIES = {
    # US states
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    "district of columbia",
    "puerto rico",
    # Canadian provinces
    "alberta",
    "british columbia",
    "manitoba",
    "new brunswick",
    "newfoundland and labrador",
    "nova scotia",
    "ontario",
    "prince edward island",
    "quebec",
    "saskatchewan",
    "yukon",
    "northwest territories",
    "nunavut",
    # UK regions
    "england",
    "scotland",
    "wales",
    "northern ireland",
    # Indian states
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "delhi",
    # Australian states
    "new south wales",
    "victoria",
    "queensland",
    "south australia",
    "western australia",
    "tasmania",
    "australian capital territory",
    "northern territory",
    # German states
    "bavaria",
    "baden-wurttemberg",
    "bavaria",
    "brandenburg",
    "hesse",
    "lower saxony",
    "mecklenburg-vorpommern",
    "north rhine-westphalia",
    "rhineland-palatinate",
    "saarland",
    "saxony",
    "saxony-anhalt",
    "schleswig-holstein",
    "thuringia",
    # Other regions
    "flanders",
    "wallonia",
    "catalonia",
    "basque country",
    "galicia",
    "andalusia",
    "ile-de-france",
    "brittany",
    "normandy",
    "provence-alpes-cote d'azur",
    "occitanie",
    "hauts-de-france",
    "grand est",
    "pays de la loire",
    "auvergne-rhone-alpes",
    "aquitaine",
    # UK regions/counties
    "greater london",
    "greater london area",
    "greater manchester",
    "berkshire",
    "hampshire",
    "surrey",
    "kent",
    "essex",
    "middlesex",
    "lancashire",
    "yorkshire",
    "cheshire",
    "hertfordshire",
    "buckinghamshire",
    "oxfordshire",
    "cambridgeshire",
    "devon",
    "cornwall",
    "somerset",
    "dorset",
    "wiltshire",
    "gloucestershire",
    "warwickshire",
    "northamptonshire",
    "leicestershire",
    "nottinghamshire",
    "derbyshire",
    "staffordshire",
    "shropshire",
    "herefordshire",
    "worcestershire",
    "west midlands",
}

# Patterns that indicate invalid city values (multi-location, addresses, etc.)
_INVALID_CITY_PATTERNS = [
    re.compile(r"^all\s+", re.IGNORECASE),  # "All Hubs", "All locations", "All Offices"
    re.compile(r"^flex\s*[-–]", re.IGNORECASE),  # "Flex - Berlin", "Flex-London"
    re.compile(r"^home[-:\s]", re.IGNORECASE),  # "Home-based", "Home Office"
    re.compile(r"\s+or\s+", re.IGNORECASE),  # "London or Dublin"
    re.compile(r";", re.IGNORECASE),  # Multi-location with semicolon
    re.compile(r"^\d+\s+\w+", re.IGNORECASE),  # Starts with number (addresses)
    re.compile(
        r"\bstreet\b|\bst\b|\bavenue\b|\bave\b|\bblvd\b|\broad\b", re.IGNORECASE
    ),  # Street addresses
    re.compile(r"^\w,\s*\w", re.IGNORECASE),  # "A, B" pattern (single letters)
    re.compile(r"^across\s+", re.IGNORECASE),  # "Across Canada", "Across Quebec"
    re.compile(r"^any", re.IGNORECASE),  # "Any Office", "Anywhere"
    re.compile(r"^beyond\s+", re.IGNORECASE),  # "Beyond Meridian", "Beyond Therapy"
    re.compile(r"^[a-zA-Z]$", re.IGNORECASE),  # Single letters A, B, C
    re.compile(r"^contract", re.IGNORECASE),  # "Contract", "Contractors"
    re.compile(r"^hybrid$", re.IGNORECASE),  # "Hybrid"
    re.compile(r"^central\s", re.IGNORECASE),  # "Central - United States", "Central Singapore"
    re.compile(r"^lt\s*-\s*", re.IGNORECASE),  # "LT - North America"
    re.compile(r"^greater\s+", re.IGNORECASE),  # "Greater London", "Greater Manchester"
]

# Country patterns with word boundaries
_COUNTRY_PATTERNS = [
    (re.compile(r"\bunited states\b", re.IGNORECASE), "United States"),
    (re.compile(r"\bunited kingdom\b", re.IGNORECASE), "United Kingdom"),
    (re.compile(r"\bcanada\b", re.IGNORECASE), "Canada"),
    (re.compile(r"\bgermany\b", re.IGNORECASE), "Germany"),
    (re.compile(r"\bfrance\b", re.IGNORECASE), "France"),
    (re.compile(r"\bindia\b", re.IGNORECASE), "India"),
    (re.compile(r"\baustralia\b", re.IGNORECASE), "Australia"),
    (re.compile(r"\bjapan\b", re.IGNORECASE), "Japan"),
    (re.compile(r"\bchina\b", re.IGNORECASE), "China"),
    (re.compile(r"\bsingapore\b", re.IGNORECASE), "Singapore"),
    (re.compile(r"\bnetherlands\b", re.IGNORECASE), "Netherlands"),
    (re.compile(r"\bspain\b", re.IGNORECASE), "Spain"),
    (re.compile(r"\bitaly\b", re.IGNORECASE), "Italy"),
    (re.compile(r"\bbrazil\b", re.IGNORECASE), "Brazil"),
    (re.compile(r"\bmexico\b", re.IGNORECASE), "Mexico"),
    (re.compile(r"\bireland\b", re.IGNORECASE), "Ireland"),
    (re.compile(r"\bswitzerland\b", re.IGNORECASE), "Switzerland"),
    (re.compile(r"\bsweden\b", re.IGNORECASE), "Sweden"),
    (re.compile(r"\bnorway\b", re.IGNORECASE), "Norway"),
    (re.compile(r"\bdenmark\b", re.IGNORECASE), "Denmark"),
    (re.compile(r"\bfinland\b", re.IGNORECASE), "Finland"),
    (re.compile(r"\bbelgium\b", re.IGNORECASE), "Belgium"),
    (re.compile(r"\baustria\b", re.IGNORECASE), "Austria"),
    (re.compile(r"\bpoland\b", re.IGNORECASE), "Poland"),
    (re.compile(r"\bukraine\b", re.IGNORECASE), "Ukraine"),
    (re.compile(r"\bromania\b", re.IGNORECASE), "Romania"),
    (re.compile(r"\bczechia\b", re.IGNORECASE), "Czechia"),
    (re.compile(r"\bczech republic\b", re.IGNORECASE), "Czechia"),
    (re.compile(r"\bhungary\b", re.IGNORECASE), "Hungary"),
    (re.compile(r"\bportugal\b", re.IGNORECASE), "Portugal"),
    (re.compile(r"\bgreece\b", re.IGNORECASE), "Greece"),
    (re.compile(r"\bisrael\b", re.IGNORECASE), "Israel"),
    (re.compile(r"\bsouth korea\b", re.IGNORECASE), "South Korea"),
    (re.compile(r"\btaiwan\b", re.IGNORECASE), "Taiwan"),
    (re.compile(r"\bhong kong\b", re.IGNORECASE), "Hong Kong"),
    (re.compile(r"\bnew zealand\b", re.IGNORECASE), "New Zealand"),
    (re.compile(r"\bsouth africa\b", re.IGNORECASE), "South Africa"),
    (re.compile(r"\bphilippines\b", re.IGNORECASE), "Philippines"),
    (re.compile(r"\bmalaysia\b", re.IGNORECASE), "Malaysia"),
    (re.compile(r"\bthailand\b", re.IGNORECASE), "Thailand"),
    (re.compile(r"\bvietnam\b", re.IGNORECASE), "Vietnam"),
    (re.compile(r"\bindonesia\b", re.IGNORECASE), "Indonesia"),
    (re.compile(r"\bturkey\b", re.IGNORECASE), "Turkey"),
    (re.compile(r"\brussia\b", re.IGNORECASE), "Russia"),
    (re.compile(r"\bkazakhstan\b", re.IGNORECASE), "Kazakhstan"),
    (re.compile(r"\buzbekistan\b", re.IGNORECASE), "Uzbekistan"),
    (re.compile(r"\bargentina\b", re.IGNORECASE), "Argentina"),
    (re.compile(r"\bchile\b", re.IGNORECASE), "Chile"),
    (re.compile(r"\bcolombia\b", re.IGNORECASE), "Colombia"),
    (re.compile(r"\bperu\b", re.IGNORECASE), "Peru"),
    (re.compile(r"\bvenezuela\b", re.IGNORECASE), "Venezuela"),
    (re.compile(r"\becuador\b", re.IGNORECASE), "Ecuador"),
    (re.compile(r"\buruguay\b", re.IGNORECASE), "Uruguay"),
    (re.compile(r"\bparaguay\b", re.IGNORECASE), "Paraguay"),
    (re.compile(r"\bbolivia\b", re.IGNORECASE), "Bolivia"),
    (re.compile(r"\bcosta rica\b", re.IGNORECASE), "Costa Rica"),
    (re.compile(r"\bguatemala\b", re.IGNORECASE), "Guatemala"),
    (re.compile(r"\bhonduras\b", re.IGNORECASE), "Honduras"),
    (re.compile(r"\bel salvador\b", re.IGNORECASE), "El Salvador"),
    (re.compile(r"\bnicaragua\b", re.IGNORECASE), "Nicaragua"),
    (re.compile(r"\bpanama\b", re.IGNORECASE), "Panama"),
    (re.compile(r"\bpuerto rico\b", re.IGNORECASE), "Puerto Rico"),
    (re.compile(r"\buae\b", re.IGNORECASE), "United Arab Emirates"),
    (re.compile(r"\bunited arab emirates\b", re.IGNORECASE), "United Arab Emirates"),
    (re.compile(r"\begypt\b", re.IGNORECASE), "Egypt"),
    (re.compile(r"\bnigeria\b", re.IGNORECASE), "Nigeria"),
    (re.compile(r"\bkenya\b", re.IGNORECASE), "Kenya"),
    (re.compile(r"\bmorocco\b", re.IGNORECASE), "Morocco"),
    (re.compile(r"\btunisia\b", re.IGNORECASE), "Tunisia"),
    (re.compile(r"\bethiopia\b", re.IGNORECASE), "Ethiopia"),
    (re.compile(r"\bsaudi arabia\b", re.IGNORECASE), "Saudi Arabia"),
    (re.compile(r"\bqatar\b", re.IGNORECASE), "Qatar"),
    (re.compile(r"\bkuwait\b", re.IGNORECASE), "Kuwait"),
    (re.compile(r"\bbahrain\b", re.IGNORECASE), "Bahrain"),
    (re.compile(r"\boman\b", re.IGNORECASE), "Oman"),
]

# Country abbreviations
_COUNTRY_ABBR_PATTERNS = [
    (re.compile(r"\busa?\b", re.IGNORECASE), "United States"),
    (re.compile(r"\buk\b", re.IGNORECASE), "United Kingdom"),
    (re.compile(r"\bde\b", re.IGNORECASE), "Germany"),
    (re.compile(r"\bfr\b", re.IGNORECASE), "France"),
    (re.compile(r"\bau\b", re.IGNORECASE), "Australia"),
    (re.compile(r"\bjp\b", re.IGNORECASE), "Japan"),
    (re.compile(r"\bcn\b", re.IGNORECASE), "China"),
    (re.compile(r"\bsg\b", re.IGNORECASE), "Singapore"),
    (re.compile(r"\bnl\b", re.IGNORECASE), "Netherlands"),
    (re.compile(r"\bes\b", re.IGNORECASE), "Spain"),
    (re.compile(r"\bit\b", re.IGNORECASE), "Italy"),
    (re.compile(r"\bbr\b", re.IGNORECASE), "Brazil"),
    (re.compile(r"\bmx\b", re.IGNORECASE), "Mexico"),
    (re.compile(r"\bie\b", re.IGNORECASE), "Ireland"),
    (re.compile(r"\bch\b", re.IGNORECASE), "Switzerland"),
    (re.compile(r"\bse\b", re.IGNORECASE), "Sweden"),
    (re.compile(r"\bno\b", re.IGNORECASE), "Norway"),
    (re.compile(r"\bdk\b", re.IGNORECASE), "Denmark"),
    (re.compile(r"\bfi\b", re.IGNORECASE), "Finland"),
    (re.compile(r"\bbe\b", re.IGNORECASE), "Belgium"),
    (re.compile(r"\bat\b", re.IGNORECASE), "Austria"),
    (re.compile(r"\bpl\b", re.IGNORECASE), "Poland"),
    (re.compile(r"\bua\b", re.IGNORECASE), "Ukraine"),
    (re.compile(r"\bro\b", re.IGNORECASE), "Romania"),
    (re.compile(r"\bcz\b", re.IGNORECASE), "Czechia"),
    (re.compile(r"\bhu\b", re.IGNORECASE), "Hungary"),
    (re.compile(r"\bpt\b", re.IGNORECASE), "Portugal"),
    (re.compile(r"\bgr\b", re.IGNORECASE), "Greece"),
    (re.compile(r"\bil\b", re.IGNORECASE), "Israel"),
    (re.compile(r"\bkr\b", re.IGNORECASE), "South Korea"),
    (re.compile(r"\btw\b", re.IGNORECASE), "Taiwan"),
    (re.compile(r"\bhk\b", re.IGNORECASE), "Hong Kong"),
    (re.compile(r"\bnz\b", re.IGNORECASE), "New Zealand"),
    (re.compile(r"\bza\b", re.IGNORECASE), "South Africa"),
    (re.compile(r"\bae\b", re.IGNORECASE), "United Arab Emirates"),
    (re.compile(r"\bph\b", re.IGNORECASE), "Philippines"),
    (re.compile(r"\bmy\b", re.IGNORECASE), "Malaysia"),
    (re.compile(r"\bth\b", re.IGNORECASE), "Thailand"),
    (re.compile(r"\bvn\b", re.IGNORECASE), "Vietnam"),
    (re.compile(r"\bid\b", re.IGNORECASE), "Indonesia"),
    (re.compile(r"\btr\b", re.IGNORECASE), "Turkey"),
    (re.compile(r"\bru\b", re.IGNORECASE), "Russia"),
    (re.compile(r"\bkz\b", re.IGNORECASE), "Kazakhstan"),
    (re.compile(r"\buz\b", re.IGNORECASE), "Uzbekistan"),
    (re.compile(r"\bcl\b", re.IGNORECASE), "Chile"),
    (re.compile(r"\bpe\b", re.IGNORECASE), "Peru"),
    (re.compile(r"\bve\b", re.IGNORECASE), "Venezuela"),
    (re.compile(r"\bec\b", re.IGNORECASE), "Ecuador"),
    (re.compile(r"\buy\b", re.IGNORECASE), "Uruguay"),
    (re.compile(r"\bpy\b", re.IGNORECASE), "Paraguay"),
    (re.compile(r"\bbo\b", re.IGNORECASE), "Bolivia"),
    (re.compile(r"\bcr\b", re.IGNORECASE), "Costa Rica"),
    (re.compile(r"\bgt\b", re.IGNORECASE), "Guatemala"),
    (re.compile(r"\bhn\b", re.IGNORECASE), "Honduras"),
    (re.compile(r"\bsv\b", re.IGNORECASE), "El Salvador"),
    (re.compile(r"\bni\b", re.IGNORECASE), "Nicaragua"),
    (re.compile(r"\bpa\b", re.IGNORECASE), "Panama"),
    (re.compile(r"\bpr\b", re.IGNORECASE), "Puerto Rico"),
    (re.compile(r"\bee\b", re.IGNORECASE), "Estonia"),
    (re.compile(r"\beg\b", re.IGNORECASE), "Egypt"),
    (re.compile(r"\bke\b", re.IGNORECASE), "Kenya"),
    (re.compile(r"\blu\b", re.IGNORECASE), "Luxembourg"),
    (re.compile(r"\bng\b", re.IGNORECASE), "Nigeria"),
    (re.compile(r"\bsa\b", re.IGNORECASE), "Saudi Arabia"),
    (re.compile(r"\blv\b", re.IGNORECASE), "Latvia"),
    (re.compile(r"\blt\b", re.IGNORECASE), "Lithuania"),
    (re.compile(r"\bsi\b", re.IGNORECASE), "Slovenia"),
    (re.compile(r"\bbg\b", re.IGNORECASE), "Bulgaria"),
    (re.compile(r"\bhr\b", re.IGNORECASE), "Croatia"),
    (re.compile(r"\bba\b", re.IGNORECASE), "Bosnia and Herzegovina"),
    (re.compile(r"\bsk\b", re.IGNORECASE), "Slovakia"),
    (re.compile(r"\bcy\b", re.IGNORECASE), "Cyprus"),
]

# Region code patterns (to strip from country)
_REGION_CODE_PATTERN = re.compile(r",?\s*(EMEA|AMER|APAC|LATAM)\s*$", re.IGNORECASE)

# Country name aliases for normalization
_COUNTRY_ALIASES = {
    "türkiye": "Turkey",
    "turkiye": "Turkey",
    "korea, republic of": "South Korea",
    "republic of korea": "South Korea",
    "the netherlands": "Netherlands",
    "russian federation": "Russia",
    "czech republic": "Czechia",
    "uae": "United Arab Emirates",
    "united arab emirates": "United Arab Emirates",
}

# Abbreviations that should only match as full country strings
_COUNTRY_ABBREV_FULL_MATCH = {
    "us": "United States",
    "u.s": "United States",
    "u.s.": "United States",
    "gb": "United Kingdom",
    "in": "India",
    "ca": "Canada",
    "tr": "Turkey",
    "rs": "Serbia",
    "es": "Spain",
    "de": "Germany",
    "fr": "France",
    "jp": "Japan",
    "br": "Brazil",
    "mx": "Mexico",
    "au": "Australia",
    "nl": "Netherlands",
    "it": "Italy",
    "ie": "Ireland",
    "ch": "Switzerland",
    "se": "Sweden",
    "no": "Norway",
    "dk": "Denmark",
    "fi": "Finland",
    "be": "Belgium",
    "at": "Austria",
    "pl": "Poland",
    "ua": "Ukraine",
    "ro": "Romania",
    "cz": "Czechia",
    "hu": "Hungary",
    "pt": "Portugal",
    "gr": "Greece",
    "il": "Israel",
    "kr": "South Korea",
    "tw": "Taiwan",
    "hk": "Hong Kong",
    "nz": "New Zealand",
    "za": "South Africa",
    "ae": "United Arab Emirates",
    "ph": "Philippines",
    "my": "Malaysia",
    "th": "Thailand",
    "vn": "Vietnam",
    "id": "Indonesia",
    "ru": "Russia",
    "kz": "Kazakhstan",
    "uz": "Uzbekistan",
    "ar": "Argentina",
    "cl": "Chile",
    "co": "Colombia",
    "pe": "Peru",
    "ve": "Venezuela",
    "ec": "Ecuador",
    "uy": "Uruguay",
    "py": "Paraguay",
    "bo": "Bolivia",
    "cr": "Costa Rica",
    "gt": "Guatemala",
    "hn": "Honduras",
    "sv": "El Salvador",
    "ni": "Nicaragua",
    "pa": "Panama",
    "pr": "Puerto Rico",
    "ee": "Estonia",
    "eg": "Egypt",
    "ke": "Kenya",
    "lu": "Luxembourg",
    "ng": "Nigeria",
    "sa": "Saudi Arabia",
    "ua": "Ukraine",
    "lv": "Latvia",
    "lt": "Lithuania",
    "si": "Slovenia",
    "bg": "Bulgaria",
    "hr": "Croatia",
    "ba": "Bosnia and Herzegovina",
    "sk": "Slovakia",
    "cy": "Cyprus",
    "mt": "Malta",
}

# Remote patterns
_REMOTE_PATTERNS = [
    re.compile(r"^remote$", re.IGNORECASE),
    re.compile(r"^remote\s+", re.IGNORECASE),
    re.compile(r"\s+remote$", re.IGNORECASE),
    re.compile(r"^remote\s*[-–,]", re.IGNORECASE),
    re.compile(r"[-–,]\s*remote", re.IGNORECASE),
]
_MULTI_LOC_DELIMITERS = re.compile(r"[;|]")

# Street extraction patterns
_STREET_TYPE_PATTERN = re.compile(
    r"^\d+\s+([NnSsEeWw]\.?\s+)?([A-Za-z]+\s+)?\b(st|street|ave|avenue|blvd|boulevard|dr\b|drive|rd|road|ln|lane|way|ct|court|pl|place|pkwy|parkway|trail|trl|cir|circle|bldv)\b[\s\.]*",
    re.IGNORECASE,
)
_SUITE_PATTERN = re.compile(r"\s+(suite|ste|apt|unit|#|lot)\s*[A-Za-z0-9\-]+", re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")

# City/state patterns
_CITY_STATE_PATTERN = re.compile(r"^([A-Za-z\s]+)\s+([A-Z]{2})$")
_STATE_ABBR_PATTERN = re.compile(r"\b([A-Z]{2})\b")
_CITY_SUFFIX_PATTERN = re.compile(r"\s+(City|Town|Village|Municipality)$", re.IGNORECASE)
_ZIP_PATTERN = re.compile(r"\s+\d{5}(-\d{4})?$")
_TRAILING_STATE_PATTERN = re.compile(r",?\s*[A-Z]{2}\s*$")


def is_street_address(text: str) -> bool:
    """Check if text looks like a street address using pre-compiled pattern."""
    return bool(_STREET_NUMBER_PATTERN.match(text.strip()))


def is_fake_city(city: str) -> bool:
    """Check if city name is fake/artificial using pre-compiled patterns."""
    if not city:
        return True

    city_lower = city.lower().strip()

    # Check fake indicators using pre-compiled patterns
    for pattern in _FAKE_CITY_PATTERNS:
        if pattern.search(city_lower):
            return True

    # Check for patterns like "Suite 1", "Remote Us"
    if _FAKE_CITY_PREFIX_PATTERN.match(city_lower):
        return True

    return False


def _normalize_country_name(country: str) -> str:
    """Normalize country name by expanding abbreviations and aliases."""
    if not country:
        return country

    # Strip whitespace
    country = country.strip()
    country_lower = country.lower()

    # Check for abbreviation full matches (US, U.S, GB, IN, etc.)
    if country_lower in _COUNTRY_ABBREV_FULL_MATCH:
        return _COUNTRY_ABBREV_FULL_MATCH[country_lower]

    # Check for aliases (alternative names)
    if country_lower in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[country_lower]

    return country


def _strip_region_codes(text: str) -> str:
    """Strip region codes like EMEA, AMER, APAC from end of text."""
    return _REGION_CODE_PATTERN.sub("", text).strip()


def extract_country_from_text(text: str) -> str | None:
    """Extract country from text using pre-compiled word boundary patterns.

    Improvements:
    - Expands abbreviations (US -> United States)
    - Normalizes alternative names (Türkiye -> Turkey)
    - Strips region codes (Germany, EMEA -> Germany)
    - Handles trailing spaces
    """
    if not text:
        return None

    # Strip region codes first
    text = _strip_region_codes(text)
    text_lower = text.lower().strip()

    # Check for abbreviation full matches first (exact match only)
    if text_lower in _COUNTRY_ABBREV_FULL_MATCH:
        return _COUNTRY_ABBREV_FULL_MATCH[text_lower]

    # Check for aliases (alternative country names)
    if text_lower in _COUNTRY_ALIASES:
        return _COUNTRY_ALIASES[text_lower]

    # Handle special case: "U.S" or "U.S." within text (e.g., "Palo Alto, CA, U.S")
    if re.search(r"\bu\.s\.?\b", text_lower):
        return "United States"

    # Check full country names using pre-compiled patterns
    for pattern, country in _COUNTRY_PATTERNS:
        if pattern.search(text_lower):
            return country

    # Check abbreviations using pre-compiled patterns (word boundary matches)
    for pattern, country in _COUNTRY_ABBR_PATTERNS:
        if pattern.search(text_lower):
            return country

    return None


def expand_state_abbreviation(state_abbr: str) -> str | None:
    """Expand US and Canadian state abbreviations."""
    states = {
        "AL": "Alabama",
        "AK": "Alaska",
        "AZ": "Arizona",
        "AR": "Arkansas",
        "CA": "California",
        "CO": "Colorado",
        "CT": "Connecticut",
        "DE": "Delaware",
        "FL": "Florida",
        "GA": "Georgia",
        "HI": "Hawaii",
        "ID": "Idaho",
        "IL": "Illinois",
        "IN": "Indiana",
        "IA": "Iowa",
        "KS": "Kansas",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "ME": "Maine",
        "MD": "Maryland",
        "MA": "Massachusetts",
        "MI": "Michigan",
        "MN": "Minnesota",
        "MS": "Mississippi",
        "MO": "Missouri",
        "MT": "Montana",
        "NE": "Nebraska",
        "NV": "Nevada",
        "NH": "New Hampshire",
        "NJ": "New Jersey",
        "NM": "New Mexico",
        "NY": "New York",
        "NC": "North Carolina",
        "ND": "North Dakota",
        "OH": "Ohio",
        "OK": "Oklahoma",
        "OR": "Oregon",
        "PA": "Pennsylvania",
        "RI": "Rhode Island",
        "SC": "South Carolina",
        "SD": "South Dakota",
        "TN": "Tennessee",
        "TX": "Texas",
        "UT": "Utah",
        "VT": "Vermont",
        "VA": "Virginia",
        "WA": "Washington",
        "WV": "West Virginia",
        "WI": "Wisconsin",
        "WY": "Wyoming",
        "DC": "District of Columbia",
        "AB": "Alberta",
        "BC": "British Columbia",
        "MB": "Manitoba",
        "NB": "New Brunswick",
        "NL": "Newfoundland and Labrador",
        "NS": "Nova Scotia",
        "NT": "Northwest Territories",
        "NU": "Nunavut",
        "ON": "Ontario",
        "PE": "Prince Edward Island",
        "QC": "Quebec",
        "SK": "Saskatchewan",
        "YT": "Yukon",
    }
    return states.get(state_abbr.upper())


def is_remote_pattern(location: str) -> bool:
    """Check if location is a remote pattern using pre-compiled patterns."""
    location_lower = location.lower().strip()

    for pattern in _REMOTE_PATTERNS:
        if pattern.search(location_lower):
            return True
    return False


def has_multiple_remote_locations(location: str) -> bool:
    """Check if location has multiple remote locations using pre-compiled patterns."""
    if ";" not in location and "|" not in location:
        return False

    parts = _MULTI_LOC_DELIMITERS.split(location)
    remote_count = sum(1 for part in parts if is_remote_pattern(part.strip()))

    return remote_count > 1 or (len(parts) > 1 and is_remote_pattern(location))


def extract_city_from_street_address(street_text: str) -> str | None:
    """Extract city name from street address text using pre-compiled patterns."""
    if not street_text:
        return None

    # Remove leading street number and type
    text = _STREET_TYPE_PATTERN.sub("", street_text)

    # Remove suite/apartment/unit info
    text = _SUITE_PATTERN.sub(" ", text)

    # Remove extra spaces
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()

    city = text.strip()

    if is_fake_city(city):
        return None

    return city if city else None


def extract_city_before_state(text: str) -> str | None:
    """Extract city that appears before state abbreviation."""
    if not text:
        return None

    parts = text.split()

    if len(parts) >= 2:
        last_part = parts[-1]
        if re.match(r"^[A-Z]{2}$", last_part):
            city = " ".join(parts[:-1])
            return city if not is_fake_city(city) else None

    if re.match(r"^[A-Z]{2}(\s+\d{5})?$", text.strip()):
        return None

    if not is_fake_city(text):
        return text.strip()

    return None


def extract_state(text: str) -> str | None:
    """Extract state from text using pre-compiled patterns and known state names.

    Note: This function extracts geographic regions that are sub-national (states, provinces).
    Countries like "UK", "Germany", etc. should NOT be extracted as states - they are countries.
    """
    if not text:
        return None

    # Remove zip code using pre-compiled pattern
    text_clean = _ZIP_PATTERN.sub("", text)
    text_clean = text_clean.strip()

    # Check special state mappings that are NOT countries
    # (e.g., "Berlin-Brandenburg" -> "Berlin", "NSW" -> "New South Wales")
    if text_clean in _STATE_NAME_MAPPINGS:
        mapped = _STATE_NAME_MAPPINGS[text_clean]
        # Don't return country names as states
        if mapped is None or mapped in [
            "Australia",
            "China",
            "Germany",
            "France",
            "India",
            "Indonesia",
            "Ireland",
            "Israel",
            "Japan",
            "Korea",
            "South Korea",
            "Netherlands",
            "Portugal",
            "Saudi Arabia",
            "Singapore",
            "Switzerland",
            "Taiwan",
            "United Arab Emirates",
            "United Kingdom",
            "United States",
            "Vietnam",
            "Argentina",
            "Bolivia",
            "Brazil",
            "Colombia",
            "Kuwait",
            "Kazakhstan",
            "Romania",
            "Thailand",
            "Hong Kong",
        ]:
            return None
        return mapped

    # Use pre-compiled state abbreviation pattern
    match = _STATE_ABBR_PATTERN.search(text_clean)
    if match:
        state_abbr = match.group(1)
        full_state = expand_state_abbreviation(state_abbr)
        if full_state:
            return full_state

    if text_clean and len(text_clean) > 2:
        text_lower = text_clean.lower()

        # US states
        us_states = [
            "alabama",
            "alaska",
            "arizona",
            "arkansas",
            "california",
            "colorado",
            "connecticut",
            "delaware",
            "florida",
            "georgia",
            "hawaii",
            "idaho",
            "illinois",
            "indiana",
            "iowa",
            "kansas",
            "kentucky",
            "louisiana",
            "maine",
            "maryland",
            "massachusetts",
            "michigan",
            "minnesota",
            "mississippi",
            "missouri",
            "montana",
            "nebraska",
            "nevada",
            "new hampshire",
            "new jersey",
            "new mexico",
            "new york",
            "north carolina",
            "north dakota",
            "ohio",
            "oklahoma",
            "oregon",
            "pennsylvania",
            "rhode island",
            "south carolina",
            "south dakota",
            "tennessee",
            "texas",
            "utah",
            "vermont",
            "virginia",
            "washington",
            "west virginia",
            "wisconsin",
            "wyoming",
            "district of columbia",
        ]

        # Canadian provinces
        canadian_provinces = [
            "alberta",
            "british columbia",
            "manitoba",
            "new brunswick",
            "newfoundland and labrador",
            "nova scotia",
            "ontario",
            "prince edward island",
            "quebec",
            "saskatchewan",
        ]

        # Indian states
        indian_states = [
            "andhra pradesh",
            "arunachal pradesh",
            "assam",
            "bihar",
            "chhattisgarh",
            "goa",
            "gujarat",
            "haryana",
            "himachal pradesh",
            "jharkhand",
            "karnataka",
            "kerala",
            "madhya pradesh",
            "maharashtra",
            "manipur",
            "meghalaya",
            "mizoram",
            "nagaland",
            "odisha",
            "punjab",
            "rajasthan",
            "sikkim",
            "tamil nadu",
            "telangana",
            "tripura",
            "uttar pradesh",
            "uttarakhand",
            "west bengal",
            "delhi",
            "jammu and kashmir",
            "ladakh",
            "puducherry",
        ]

        # Australian states/territories
        australian_states = [
            "new south wales",
            "victoria",
            "queensland",
            "south australia",
            "western australia",
            "tasmania",
            "australian capital territory",
            "northern territory",
        ]

        # German states (Bundesländer)
        german_states = [
            "baden-württemberg",
            "bavaria",
            "bayern",
            "berlin",
            "brandenburg",
            "bremen",
            "hamburg",
            "hesse",
            "hessen",
            "lower saxony",
            "mecklenburg-vorpommern",
            "north rhine-westphalia",
            "nordrhein-westfalen",
            "rhineland-palatinate",
            "saarland",
            "saxony",
            "sachsen",
            "saxony-anhalt",
            "schleswig-holstein",
            "thuringia",
            "thüringen",
        ]

        # UK regions
        uk_regions = [
            "england",
            "scotland",
            "wales",
            "northern ireland",
            "greater london",
            "london",
        ]

        # French regions (for region-level recognition)
        french_regions = [
            "île-de-france",
            "auvergne-rhône-alpes",
            "hauts-de-france",
            "nouvelle-aquitaine",
            "occitanie",
            "grand est",
            "provence-alpes-côte d'azur",
            "pays de la loire",
            "bretagne",
            "normandie",
            "bourgogne-franche-comté",
            "centre-val de loire",
            "corse",
        ]

        # Italian regions
        italian_regions = [
            "abruzzo",
            "aosta valley",
            "apulia",
            "basilicata",
            "calabria",
            "campania",
            "emilia-romagna",
            "friuli-venezia giulia",
            "lazio",
            "liguria",
            "lombardy",
            "lombardia",
            "marche",
            "molise",
            "piedmont",
            "piemonte",
            "sardinia",
            "sardegna",
            "sicily",
            "sicilia",
            "tuscany",
            "toscana",
            "trentino-alto adige",
            "umbria",
            "veneto",
        ]

        # Spanish regions
        spanish_regions = [
            "andalusia",
            "andalucía",
            "aragon",
            "aragón",
            "asturias",
            "balearic islands",
            "islas baleares",
            "basque country",
            "país vasco",
            "canary islands",
            "islas canarias",
            "cantabria",
            "castile and león",
            "castilla y león",
            "castile-la mancha",
            "castilla-la mancha",
            "catalonia",
            "catalunya",
            "extremadura",
            "galicia",
            "la rioja",
            "madrid",
            "murcia",
            "navarre",
            "navarra",
            "valencia",
            "valencian community",
        ]

        # Mexican states
        mexican_states = [
            "aguascalientes",
            "baja california",
            "baja california sur",
            "campeche",
            "chiapas",
            "chihuahua",
            "coahuila",
            "colima",
            "durango",
            "guanajuato",
            "guerrero",
            "hidalgo",
            "jalisco",
            "mexico",
            "méxico",
            "michoacán",
            "morelos",
            "nayarit",
            "nuevo león",
            "oaxaca",
            "puebla",
            "querétaro",
            "quintana roo",
            "san luis potosí",
            "sinaloa",
            "sonora",
            "tabasco",
            "tamaulipas",
            "tlaxcala",
            "veracruz",
            "yucatán",
            "zacatecas",
            "ciudad de méxico",
            "mexico city",
        ]

        # Brazilian states
        brazilian_states = [
            "acre",
            "alagoas",
            "amapá",
            "amazonas",
            "bahia",
            "ceará",
            "distrito federal",
            "espírito santo",
            "goiás",
            "maranhão",
            "mato grosso",
            "mato grosso do sul",
            "minas gerais",
            "pará",
            "paraíba",
            "paraná",
            "pernambuco",
            "piauí",
            "rio de janeiro",
            "rio grande do norte",
            "rio grande do sul",
            "rondônia",
            "roraima",
            "santa catarina",
            "são paulo",
            "sergipe",
            "tocantins",
        ]

        # All known states for lookup
        all_known_states = (
            us_states
            + canadian_provinces
            + indian_states
            + australian_states
            + german_states
            + uk_regions
            + french_regions
            + italian_regions
            + spanish_regions
            + mexican_states
            + brazilian_states
        )

        if text_lower in all_known_states:
            return text_clean.title()

    return None


# State name normalization mappings
# NOTE: normalize_state_name() strips whitespace before lookup, so keys should not have trailing spaces
_STATE_NAME_MAPPINGS = {
    # === US STATE VARIATIONS ===
    "Washington D.C.": "District of Columbia",
    "Washington, D.C.": "District of Columbia",
    "Washington D.C": "District of Columbia",
    "District Of Columbia": "District of Columbia",
    "New York State": "New York",
    "Washington State": "Washington",
    "NY": "New York",
    "California, Washington": None,
    "Seattle, Washington": "Washington",
    "San Francisco, Seattle": None,
    # === ACCENTED CHARACTERS -> ASCII ===
    "São Paulo": "Sao Paulo",
    "Québec": "Quebec",
    "Córdoba": "Cordoba",
    "Karnātaka": "Karnataka",
    "Mahārāshtra": "Maharashtra",
    "Telangāna": "Telangana",
    "Rājasthān": "Rajasthan",
    "México": "Mexico",
    "Nuevo León": "Nuevo Leon",
    "Ceará": "Ceara",
    "Espírito Santo": "Espirito Santo",
    "Kraków": "Krakow",
    # === FRENCH REGIONS ===
    "Ile de France": "Île-de-France",
    "Ile-De-France": "Île-de-France",
    "Ile-de-France": "Île-de-France",
    "Île-De-France": "Île-de-France",
    "Hauts-De-France": "Hauts-de-France",
    "Pays De La Loire": "Pays de la Loire",
    "Bretagne": "Brittany",
    "Brittany": "Brittany",
    "Alsace": "Grand Est",
    "Grand Est": "Grand Est",
    "Occitanie": "Occitanie",
    # === GERMAN STATES ===
    "Bayern": "Bavaria",
    "Nordrhein-Westfalen": "North Rhine-Westphalia",
    "Northrhine-Westfalia": "North Rhine-Westphalia",
    "North Rhine Westphalia": "North Rhine-Westphalia",
    "Thüringen": "Thuringia",
    # === ITALIAN REGIONS ===
    "Toscana": "Tuscany",
    "Milano": None,
    "Roma": None,
    "Firenze": None,
    "Florence": None,
    "Rome": None,
    "Milan": None,
    # === SPANISH REGIONS ===
    "Comunidad de Madrid": None,
    "Community of Madrid": None,
    "Comunidad Valenciana": "Valencia",
    "País Vasco": "Basque Country",
    "Islas Baleares": "Balearic Islands",
    "Murcia": "Murcia",
    "Santander": None,
    # === BRAZILIAN STATES (keep - these are valid) ===
    "Rio De Janeiro": "Rio de Janeiro",
    "Rio Grande Do Norte": "Rio Grande do Norte",
    "Rio Grande Do Sul": "Rio Grande do Sul",
    # === MEXICAN STATES ===
    "Ciudad de Mexico": None,
    "Mexico City": None,
    # === CANADIAN PROVINCES ===
    "Newfoundland And Labrador": "Newfoundland and Labrador",
    # === UK/LONDON VARIATIONS -> None ===
    "London": None,
    "London, City of": None,
    "London, United Kingdom": None,
    "Greater London": None,
    "England": None,
    "Scotland": None,
    "Wales": None,
    "Northern Ireland": None,
    "Berkshire": None,
    "Gloucestershire": None,
    "Hampshire": None,
    "Middlesex": None,
    "Midlothian": None,
    "Camden": None,
    "Ealing": None,
    "Newham": None,
    "Southwark": None,
    "Hammersmith and Fulham": None,
    "Bristol": None,
    "Bristol, City of": None,
    "Leeds": None,
    "Manchester": None,
    "Liverpool": None,
    "Sheffield": None,
    "Glasgow": None,
    "Edinburgh": None,
    # === NETHERLANDS PROVINCES ===
    "Noord-Holland": "North Holland",
    "North Holland": "North Holland",
    "North Brabant": "North Brabant",
    "South Holland": "South Holland",
    # === AUSTRALIAN STATES ===
    "NSW": "New South Wales",
    "Victoria": "Victoria",
    "Queensland": "Queensland",
    "South Australia": "South Australia",
    "Western Australia": "Western Australia",
    "Tasmania": "Tasmania",
    "Australian Capital Territory": "Australian Capital Territory",
    "Northern Territory": "Northern Territory",
    "Canberra": None,
    # === SPELLING CORRECTIONS ===
    "Manilla": None,
    "Ha Noi": None,
    "Karnaka": "Karnataka",
    "Guateng": "Gauteng",
    # === MAJOR CITIES -> None ===
    "Tokyo": None,
    "Jakarta": None,
    "Singapore": None,
    "Hong Kong": None,
    "Seoul": None,
    "Shanghai": None,
    "Beijing": None,
    "Shenzhen": None,
    "Dubai": None,
    "Abu Dhabi": None,
    "Amsterdam": None,
    "Rotterdam": None,
    "Brussels": None,
    "Brussels-Capital Region": None,
    "Paris": None,
    "Berlin": None,
    "Berlin-Brandenburg": None,
    "Berlin/Brandenburg": None,
    "Berlin/ Brandenburg metropolitan region": None,
    "Munich": None,
    "Hamburg": None,
    "Frankfurt": None,
    "Vienna": None,
    "Zurich": None,
    "Geneva": None,
    "Bern": None,
    "Lugano": None,
    "Vaud": None,
    "Zug": None,
    "Stockholm": None,
    "Oslo": None,
    "Copenhagen": None,
    "Helsinki": None,
    "Lisbon": None,
    "Prague": None,
    "Warsaw": None,
    "Budapest": None,
    "Athens": None,
    "Dublin": None,
    "Sydney": None,
    "Melbourne": None,
    "Brisbane": None,
    "Perth": None,
    "Auckland": None,
    "Toronto": None,
    "Vancouver": None,
    "Montreal": None,
    "Calgary": None,
    "Ottawa": None,
    "Mexico City": None,
    "Birmingham": None,
    "Boston": None,
    "Miami": None,
    "Delhi": None,
    "Buenos Aires": None,
    "Santiago": None,
    "Lima": None,
    "Bogota": None,
    "Tel Aviv": None,
    "Jerusalem": None,
    "Riyadh": None,
    "Riyadh Province": None,
    "Cairo": None,
    "Lagos": None,
    "Nairobi": None,
    "Cape Town": None,
    "Johannesburg": None,
    "Bangkok": None,
    "Kuala Lumpur": None,
    "Manila": None,
    "Ho Chi Minh City": None,
    "Hanoi": None,
    "Taipei": None,
    "Kyiv": None,
    "Riga": None,
    "Vilnius": None,
    "Ljubljana": None,
    "Zagreb": None,
    "Grad Zagreb": None,
    "Bratislava": None,
    "Belgrade": None,
    "Tehran": None,
    "Tbilisi": None,
    "Sofia": None,
    "Krakow": None,
    "New Delhi": None,
    "Hangzhou": None,
    "Qingdao": None,
    "Osaka": None,
    "Giza": None,
    "Catanzaro": None,
    "Cordoba": None,
    "Barcelona": None,
    "Madrid": None,
    "Harare": None,
    "Lefkosia": None,
    "Limassol": None,
    "Yokne'am": None,
    "Bnei Brak": None,
    "Gush Dan": None,
    "Heredia": None,
    "Ankara": None,
    "Livadia": None,
    "Angre": None,
    "Baki": None,
    "Arequipa": None,
    "Faro": None,
    "Santander": None,
    "Lugano": None,
    "Shanghai Shi": None,
    "East China": None,
    "Kanto": None,
    "Tokyo Metropolis": None,
    "Gyeonggi Province": None,
    "Central Singapore": None,
    "Orchard Road": None,
    "National Capital Region": None,
    "National Capital Region (Manila)": None,
    "Capital Region": None,
    # === COUNTRIES -> None ===
    "Australia": None,
    "China": None,
    "Germany": None,
    "France": None,
    "India": None,
    "Indonesia": None,
    "Ireland": None,
    "Israel": None,
    "Japan": None,
    "Korea": None,
    "Netherlands": None,
    "Portugal": None,
    "Saudi Arabia": None,
    "South Korea": None,
    "Switzerland": None,
    "Taiwan": None,
    "UAE": None,
    "UK": None,
    "United Kingdom": None,
    "United States": None,
    "US": None,
    "Vietnam": None,
    "Argentina": None,
    "Bolivia": None,
    "Brazil": None,
    "Mexico": None,
    "Colombia": None,
    "Kuwait": None,
    "Kazakhstan": None,
    "Romania": None,
    "Thailand": None,
    "Croatia": None,
    "Canada": None,
    "Turkey": None,
    "Norway": None,
    "Sweden": None,
    "Denmark": None,
    "Finland": None,
    "Poland": None,
    "Austria": None,
    "Czechia": None,
    "Czech Republic": None,
    "Hungary": None,
    "Greece": None,
    "Philippines": None,
    "Malaysia": None,
    "New Zealand": None,
    "South Africa": None,
    "Nigeria": None,
    "Kenya": None,
    "Egypt": None,
    "Pakistan": None,
    "Bangladesh": None,
    "Chile": None,
    "Peru": None,
    "Ecuador": None,
    "Venezuela": None,
    "Bosnia and Herzegovina": None,
    # === TRAILING SPACE VARIATIONS -> None ===
    "Canada ": None,
    "Jakarta ": None,
    "Tokyo ": None,
    # === INVALID/ADDRESS VALUES -> None ===
    "Remote": None,
    "Hybrid": None,
    "EU": None,
    "Europe": None,
    "United States & Canada": None,
    "United States Minor Outlying Islands": None,
    "FORA, Albert House, 256-260 Old Street, London, EC1V 9DD": None,
    "Kleine-Gartmanplantsoen 21, 1017RP, Amsterdam": None,
    "Gangnam": None,
    # === VALID STATES (keep as-is for normalization) ===
    "New South Wales": "New South Wales",
}


def infer_country_from_state(state: str | None) -> str | None:
    """Infer country from state/province name."""
    if not state:
        return None

    state_lower = state.lower()

    # Canadian provinces
    canadian_provinces = [
        "alberta",
        "british columbia",
        "manitoba",
        "new brunswick",
        "newfoundland and labrador",
        "nova scotia",
        "ontario",
        "prince edward island",
        "quebec",
        "saskatchewan",
        "yukon",
        "northwest territories",
        "nunavut",
    ]
    if state_lower in canadian_provinces:
        return "Canada"

    # US states
    us_states = [
        "alabama",
        "alaska",
        "arizona",
        "arkansas",
        "california",
        "colorado",
        "connecticut",
        "delaware",
        "florida",
        "georgia",
        "hawaii",
        "idaho",
        "illinois",
        "indiana",
        "iowa",
        "kansas",
        "kentucky",
        "louisiana",
        "maine",
        "maryland",
        "massachusetts",
        "michigan",
        "minnesota",
        "mississippi",
        "missouri",
        "montana",
        "nebraska",
        "nevada",
        "new hampshire",
        "new jersey",
        "new mexico",
        "new york",
        "north carolina",
        "north dakota",
        "ohio",
        "oklahoma",
        "oregon",
        "pennsylvania",
        "rhode island",
        "south carolina",
        "south dakota",
        "tennessee",
        "texas",
        "utah",
        "vermont",
        "virginia",
        "washington",
        "west virginia",
        "wisconsin",
        "wyoming",
        "district of columbia",
    ]
    if state_lower in us_states:
        return "United States"

    # Indian states
    indian_states = [
        "andhra pradesh",
        "arunachal pradesh",
        "assam",
        "bihar",
        "chhattisgarh",
        "goa",
        "gujarat",
        "haryana",
        "himachal pradesh",
        "jharkhand",
        "karnataka",
        "kerala",
        "madhya pradesh",
        "maharashtra",
        "manipur",
        "meghalaya",
        "mizoram",
        "nagaland",
        "odisha",
        "punjab",
        "rajasthan",
        "sikkim",
        "tamil nadu",
        "telangana",
        "tripura",
        "uttar pradesh",
        "uttarakhand",
        "west bengal",
        "delhi",
    ]
    if state_lower in indian_states:
        return "India"

    # Australian states
    australian_states = [
        "new south wales",
        "victoria",
        "queensland",
        "south australia",
        "western australia",
        "tasmania",
        "australian capital territory",
        "northern territory",
    ]
    if state_lower in australian_states:
        return "Australia"

    # German states
    german_states = [
        "baden-württemberg",
        "bavaria",
        "bayern",
        "berlin",
        "brandenburg",
        "bremen",
        "hamburg",
        "hesse",
        "hessen",
        "lower saxony",
        "mecklenburg-vorpommern",
        "north rhine-westphalia",
        "nordrhein-westfalen",
        "rhineland-palatinate",
        "saarland",
        "saxony",
        "sachsen",
        "saxony-anhalt",
        "schleswig-holstein",
        "thuringia",
        "thüringen",
    ]
    if state_lower in german_states:
        return "Germany"

    return None


def normalize_state_name(state: str | None) -> str | None:
    """Normalize state name by fixing variations and accents.

    This ensures consistent state naming across the database.
    """
    if not state:
        return state

    # Strip whitespace
    state = state.strip()

    # Check for exact matches in mapping
    if state in _STATE_NAME_MAPPINGS:
        return _STATE_NAME_MAPPINGS[state]

    return state


def clean_city_name(city: str | None) -> str | None:
    """Clean city name by removing common suffixes and validating against invalid values."""
    if not city:
        return None

    city = city.strip()

    # Check if city is actually a country
    if city.lower() in _COUNTRIES_AS_CITIES:
        return None

    # Check if city is actually a state/province/region
    # But skip this check for major cities that share names with states
    major_city_state_names = {
        "new york",
        "washington",
        "georgia",
        "virginia",
        "colorado",
        "oregon",
        "delhi",
        "goa",
        "gujarat",
        "kerala",
    }
    if city.lower() in _STATES_AS_CITIES and city.lower() not in major_city_state_names:
        return None

    # Check against invalid city patterns (multi-location, addresses, etc.)
    for pattern in _INVALID_CITY_PATTERNS:
        if pattern.search(city):
            return None

    # Handle "Country - City" or "Region - City" patterns
    # e.g., "Australia - Sydney" -> "Sydney", "India - Pune" -> "Pune"
    if " - " in city:
        parts = city.split(" - ", 1)
        if len(parts) == 2:
            potential_city = parts[1].strip()
            # Verify the first part is a country/region and second is a valid city
            first_part = parts[0].strip().lower()
            if first_part in _COUNTRIES_AS_CITIES or first_part in _STATES_AS_CITIES:
                # Extract just the city part
                city = potential_city
                # Re-validate the extracted city
                if city.lower() in _COUNTRIES_AS_CITIES:
                    return None
                if city.lower() in _STATES_AS_CITIES and city.lower() not in major_city_state_names:
                    return None

    # Remove state abbreviation if present
    city = _TRAILING_STATE_PATTERN.sub("", city)

    # Remove common suffixes
    city = _CITY_SUFFIX_PATTERN.sub("", city)

    # Remove zip codes
    city = _ZIP_PATTERN.sub("", city)

    city = city.strip()

    # After cleaning, check again if it's a country/state
    if city.lower() in _COUNTRIES_AS_CITIES:
        return None
    if city.lower() in _STATES_AS_CITIES and city.lower() not in major_city_state_names:
        return None

    return city if city else None


def infer_country_from_city(city: str | None) -> str | None:
    """Infer country from city name using lookup table."""
    if not city or is_fake_city(city):
        return None

    city_lower = city.lower()

    # US cities (major cities only - full list would be too long)
    us_cities = {
        "new york",
        "new york city",
        "los angeles",
        "chicago",
        "houston",
        "phoenix",
        "philadelphia",
        "san antonio",
        "san diego",
        "dallas",
        "san jose",
        "austin",
        "jacksonville",
        "fort worth",
        "columbus",
        "charlotte",
        "san francisco",
        "indianapolis",
        "seattle",
        "denver",
        "washington",
        "boston",
        "el paso",
        "detroit",
        "nashville",
        "portland",
        "oklahoma city",
        "las vegas",
        "louisville",
        "baltimore",
        "milwaukee",
        "albuquerque",
        "tucson",
        "fresno",
        "sacramento",
        "mesa",
        "kansas city",
        "atlanta",
        "long beach",
        "colorado springs",
        "raleigh",
        "miami",
        "virginia beach",
        "omaha",
        "oakland",
        "minneapolis",
        "tulsa",
        "arlington",
        "wichita",
        "bakersfield",
        "aurora",
        "tampa",
        "anaheim",
        "santa ana",
        "corpus christi",
        "riverside",
        "lexington",
        "stockton",
        "henderson",
        "saint paul",
        "st. paul",
        "cincinnati",
        "pittsburgh",
        "greensboro",
        "anchorage",
        "plano",
        "lincoln",
        "orlando",
        "irvine",
        "newark",
        "toledo",
        "durham",
        "chula vista",
        "fort wayne",
        "jersey city",
        "st. petersburg",
        "saint petersburg",
        "laredo",
        "madison",
        "chandler",
        "buffalo",
        "lubbock",
        "scottsdale",
        "reno",
        "glendale",
        "gilbert",
        "winston-salem",
        "chesapeake",
        "garland",
        "irving",
        "north las vegas",
        "norfolk",
        "fremont",
        "paradise",
        "richmond",
        "hialeah",
        "boise",
        "spokane",
        "baton rouge",
        "des moines",
        "tacoma",
        "san bernardino",
        "modesto",
        "fontana",
        "santa clarita",
        "birmingham",
        "oxnard",
        "fayetteville",
        "rochester",
        "moreno valley",
        "glendale",
        "yonkers",
        "huntington beach",
        "aurora",
        "salt lake city",
        "south salt lake",
        "amarillo",
        "montgomery",
        "little rock",
        "akron",
        "shreveport",
        "augusta",
        "grand rapids",
        "mobile",
        "huntington",
        "columbus",
        "vancouver",
        "providence",
        "knoxville",
        "fort lauderdale",
        "salem",
        "elk grove",
        "pembroke pines",
        "peoria",
        "sioux falls",
        "springfield",
        "rockford",
        "gastonia",
        "sunnyvale",
        "bellevue",
        "lakewood",
        "visalia",
        "clarksville",
        "hollywood",
        "pasadena",
        "naperville",
        "mcallen",
        "dayton",
        "harrisburg",
        "murfreesboro",
        "fullerton",
        "mesquite",
        "orange",
        "killeen",
        "frisco",
        "hampton",
        "warren",
        "mchenry",
        "edmond",
        "fairfax",
        "midland",
    }

    if city_lower in us_cities:
        return "United States"

    # International cities
    international_cities = {
        # UK
        "london": "United Kingdom",
        "manchester": "United Kingdom",
        "birmingham": "United Kingdom",
        "liverpool": "United Kingdom",
        "glasgow": "United Kingdom",
        "leeds": "United Kingdom",
        "sheffield": "United Kingdom",
        "edinburgh": "United Kingdom",
        "bristol": "United Kingdom",
        "cardiff": "United Kingdom",
        "belfast": "United Kingdom",
        "nottingham": "United Kingdom",
        # France
        "paris": "France",
        "lyon": "France",
        "marseille": "France",
        "toulouse": "France",
        "nice": "France",
        "nantes": "France",
        "strasbourg": "France",
        "montpellier": "France",
        "bordeaux": "France",
        "lille": "France",
        # Germany
        "berlin": "Germany",
        "munich": "Germany",
        "hamburg": "Germany",
        "cologne": "Germany",
        "frankfurt": "Germany",
        "stuttgart": "Germany",
        "dusseldorf": "Germany",
        "dortmund": "Germany",
        "essen": "Germany",
        "leipzig": "Germany",
        "bremen": "Germany",
        "dresden": "Germany",
        # China
        "beijing": "China",
        "shanghai": "China",
        "guangzhou": "China",
        "shenzhen": "China",
        "chengdu": "China",
        "hangzhou": "China",
        "wuhan": "China",
        "xian": "China",
        "nanjing": "China",
        "chongqing": "China",
        "tianjin": "China",
        "suzhou": "China",
        # Japan
        "tokyo": "Japan",
        "osaka": "Japan",
        "kyoto": "Japan",
        "yokohama": "Japan",
        "nagoya": "Japan",
        "sapporo": "Japan",
        "fukuoka": "Japan",
        "kobe": "Japan",
        "kawasaki": "Japan",
        # South Korea
        "seoul": "South Korea",
        "busan": "South Korea",
        "incheon": "South Korea",
        "daegu": "South Korea",
        "daejeon": "South Korea",
        # Singapore
        "singapore": "Singapore",
        # Hong Kong
        "hong kong": "Hong Kong",
        # Taiwan
        "taipei": "Taiwan",
        "taichung": "Taiwan",
        "kaohsiung": "Taiwan",
        # Australia
        "sydney": "Australia",
        "melbourne": "Australia",
        "brisbane": "Australia",
        "perth": "Australia",
        "adelaide": "Australia",
        # Canada
        "toronto": "Canada",
        "vancouver": "Canada",
        "montreal": "Canada",
        "calgary": "Canada",
        "ottawa": "Canada",
        "edmonton": "Canada",
        "winnipeg": "Canada",
        "quebec": "Canada",
        "hamilton": "Canada",
        # India
        "mumbai": "India",
        "delhi": "India",
        "bangalore": "India",
        "bengaluru": "India",
        "hyderabad": "India",
        "chennai": "India",
        "kolkata": "India",
        "pune": "India",
        "ahmedabad": "India",
        "jaipur": "India",
        "gurgaon": "India",
        "gurugram": "India",
        "noida": "India",
        # Netherlands
        "amsterdam": "Netherlands",
        "rotterdam": "Netherlands",
        # Switzerland
        "zurich": "Switzerland",
        "geneva": "Switzerland",
        # Spain
        "madrid": "Spain",
        "barcelona": "Spain",
        "valencia": "Spain",
        # Italy
        "milan": "Italy",
        "rome": "Italy",
        "naples": "Italy",
        "turin": "Italy",
        # Ireland
        "dublin": "Ireland",
        # Sweden
        "stockholm": "Sweden",
        # Denmark
        "copenhagen": "Denmark",
        # Norway
        "oslo": "Norway",
        # Finland
        "helsinki": "Finland",
        # Belgium
        "brussels": "Belgium",
        # Austria
        "vienna": "Austria",
        # Poland
        "warsaw": "Poland",
        # Czech
        "prague": "Czechia",
        # Hungary
        "budapest": "Hungary",
        # Romania
        "bucharest": "Romania",
        # Portugal
        "lisbon": "Portugal",
        # Greece
        "athens": "Greece",
        # Israel
        "tel aviv": "Israel",
        "jerusalem": "Israel",
        # UAE
        "dubai": "United Arab Emirates",
        "abu dhabi": "United Arab Emirates",
        # Brazil
        "sao paulo": "Brazil",
        "rio de janeiro": "Brazil",
        # Mexico
        "mexico city": "Mexico",
        # Argentina
        "buenos aires": "Argentina",
        # Chile
        "santiago": "Chile",
        # Colombia
        "bogota": "Colombia",
        # South Africa
        "johannesburg": "South Africa",
        "cape town": "South Africa",
        # New Zealand
        "auckland": "New Zealand",
        "wellington": "New Zealand",
        # Russia
        "moscow": "Russia",
        # Turkey
        "istanbul": "Turkey",
        # Thailand
        "bangkok": "Thailand",
        # Malaysia
        "kuala lumpur": "Malaysia",
        # Indonesia
        "jakarta": "Indonesia",
        # Philippines
        "manila": "Philippines",
        # Vietnam
        "ho chi minh city": "Vietnam",
        "hanoi": "Vietnam",
        # Egypt
        "cairo": "Egypt",
        # Nigeria
        "lagos": "Nigeria",
        # Kenya
        "nairobi": "Kenya",
    }

    return international_cities.get(city_lower)


def normalize_location(location: str | None) -> dict[str, Any]:
    """
    Normalize location string into city, state, country.

    This is the main entry point - replaces the old geostring-based parser.
    """
    empty_result = {
        "full": location,
        "city": None,
        "state": None,
        "country": None,
        "all_cities": None,
        "is_remote": False,
        "is_multi_location": False,
    }

    if not location or not location.strip():
        return empty_result

    location_clean = location.strip()
    location_lower = location_clean.lower()

    # Check for multiple remote locations
    if has_multiple_remote_locations(location_clean):
        return {
            **empty_result,
            "is_remote": True,
            "is_multi_location": True,
        }

    # Check for simple remote
    if location_lower == "remote":
        return {
            **empty_result,
            "is_remote": True,
        }

    # Check for remote with country (e.g., "Remote - US") - must start with "Remote"
    if location_lower.startswith("remote") and is_remote_pattern(location_clean):
        country = extract_country_from_text(location_clean)
        return {
            **empty_result,
            "country": country,
            "is_remote": True,
        }

    # Try to extract country from full location first
    country = extract_country_from_text(location_clean)

    # Split by comma
    parts = [p.strip() for p in location_clean.split(",")]
    parts = [p for p in parts if p]

    # Check if location ends with remote/hybrid indicator
    is_remote_job = False
    if parts and parts[-1].lower() in ["remote", "hybrid", "virtual", "work from home", "wfh"]:
        parts = parts[:-1]
        is_remote_job = True
        if not parts:
            return {
                **empty_result,
                "country": country,
                "is_remote": True,
            }

    if not parts:
        return empty_result

    # Handle multi-location (take first only)
    if len(parts) == 1 and (";" in parts[0] or "|" in parts[0]):
        first_loc = parts[0].split(";")[0].split("|")[0].strip()
        parts = [first_loc]

    city = None
    state = None

    # Parse remaining parts
    if len(parts) == 1:
        first_part = parts[0]

        if is_street_address(first_part):
            city = extract_city_from_street_address(first_part)
            if not city:
                city = extract_city_before_state(first_part)
            state = extract_state(first_part)
        elif is_fake_city(first_part):
            city = None
        else:
            # Check if this single part is a known country name
            potential_country = extract_country_from_text(first_part)
            if potential_country and first_part.lower() in [
                "united states",
                "us",
                "usa",
                "u.s.",
                "u.s",
                "united kingdom",
                "uk",
                "canada",
                "australia",
                "germany",
                "france",
                "india",
                "japan",
                "china",
                "brazil",
                "mexico",
                "spain",
                "italy",
                "netherlands",
                "singapore",
                "switzerland",
                "ireland",
                "israel",
                "south korea",
                "taiwan",
                "hong kong",
                "sweden",
                "norway",
                "denmark",
                "finland",
                "belgium",
                "austria",
                "poland",
                "portugal",
                "argentina",
                "chile",
            ]:
                # Single country name - no city/state
                country = potential_country
                city = None
                state = None
            else:
                # Check for "City TX" pattern using pre-compiled pattern
                city_state_match = _CITY_STATE_PATTERN.match(first_part.strip())
                if city_state_match:
                    potential_city = city_state_match.group(1).strip()
                    state_abbr = city_state_match.group(2)
                    if not is_fake_city(potential_city):
                        city = potential_city
                        state = expand_state_abbreviation(state_abbr)
                else:
                    # For single part, check if it's a major city that can infer country
                    # (prefer city interpretation over state interpretation)
                    inferred_country = infer_country_from_city(first_part)
                    if inferred_country:
                        city = first_part
                        country = inferred_country
                    # Check if this single part is a known state/province name
                    elif extract_state(first_part):
                        state = extract_state(first_part)
                        city = None
                    else:
                        city = first_part

    elif len(parts) == 2:
        first, second = parts[0], parts[1]

        # Special case: two DIFFERENT US states (e.g., "California, Washington") - data bug
        # Note: "New York, NY" is valid because city and state have the same name
        first_state = extract_state(first)
        second_state = extract_state(second)
        if first_state and second_state and first_state != second_state:
            # Two different states - this is ambiguous/bad data
            return {
                **empty_result,
                "country": "United States",
            }

        if is_street_address(first):
            city = extract_city_from_street_address(first)
            state = extract_state(second)

            if not city:
                city = extract_city_before_state(second)
        else:
            # Try to extract state FIRST (important: CA, NY, etc. are state abbreviations)
            state = extract_state(second)

            if state:
                # Second part is a state - use first part as city
                city = first if not is_fake_city(first) else None
            else:
                # Check if second part is a country
                second_country = extract_country_from_text(second)
                if second_country and len(second.strip()) <= 20:
                    # Check if first part is actually a state (e.g., "Pennsylvania, United States")
                    first_state = extract_state(first)
                    if first_state and infer_country_from_state(first_state) == second_country:
                        # First part is a state in this country - use it as state, not city
                        state = first_state
                        city = None
                        country = second_country
                    else:
                        city = first if not is_fake_city(first) else None
                        country = second_country
                        state = None
                else:
                    city = first if not is_fake_city(first) else None

    elif len(parts) >= 3:
        if is_street_address(parts[0]):
            city = parts[1] if not is_fake_city(parts[1]) else None
            state = extract_state(parts[2]) if len(parts) > 2 else None
        else:
            city = parts[0] if not is_fake_city(parts[0]) else None
            potential_state = extract_state(parts[1])

            # Don't treat a repeated city name as a state
            # (e.g., "Singapore, Singapore, Singapore" or "Tokyo, Tokyo, Japan")
            if potential_state and city and potential_state.lower() == city.lower():
                state = None
            else:
                state = potential_state

            # Also check parts[2] for country if state wasn't found
            if not state and len(parts) > 2:
                potential_country = extract_country_from_text(parts[2])
                if potential_country:
                    country = potential_country

    # Normalize state name (fix DC variations, accents, etc.)
    if state:
        state = normalize_state_name(state)

    # Clean city name
    if city:
        city = clean_city_name(city)
        if city and city.lower() not in location_lower:
            city = None

    # Infer country - prefer state-based inference FIRST
    # (e.g., "Vancouver, BC" should be Canada, not US)
    if not country:
        country = infer_country_from_state(state)

    # Only infer from city if state didn't provide a country
    inferred_from_city = None
    if not country and city:
        inferred_from_city = infer_country_from_city(city)

    # If city is actually a country or state/region (not a real city), clear it
    # Use the validation sets, NOT normalize_state_name() which incorrectly
    # treats valid cities like "Vancouver" as invalid
    if city:
        city_lower = city.lower()
        # Cities that share names with states should be kept (e.g., New York, Washington)
        major_city_state_names = {
            "new york",
            "washington",
            "delhi",
            "goa",
        }
        if city_lower in _COUNTRIES_AS_CITIES:
            # This is a country, not a city - clear it
            if inferred_from_city:
                country = inferred_from_city
            city = None
        elif city_lower in _STATES_AS_CITIES and city_lower not in major_city_state_names:
            # This is a state/region, not a city - clear it
            if inferred_from_city:
                country = inferred_from_city
            city = None

    # Final fallback: infer from city if still no country
    if not country and city:
        country = infer_country_from_city(city)

    # Build full location string
    full_parts = [p for p in [city, state, country] if p]
    full_location = ", ".join(full_parts) if full_parts else location_clean

    return {
        "full": full_location,
        "city": city,
        "state": state,
        "country": country,
        "all_cities": city,
        "is_remote": is_remote_job,
        "is_multi_location": False,
    }
