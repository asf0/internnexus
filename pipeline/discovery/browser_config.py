"""Configuration for headless browser discovery."""

# Countries to search
COUNTRIES = [
    "United States",
    "Brazil",
    "Korea",
    "Ireland",
    "Canada",
    "United Kingdom",
    "Germany",
]

# Job board domains (for Google site search)
JOB_BOARDS = {
    "lever": "jobs.lever.co",
    "greenhouse": "boards.greenhouse.io",
    "ashby": "jobs.ashbyhq.com",
}

# Batch configuration
SEARCHES_PER_BATCH = 3

# Delay configuration (seconds)
MIN_DELAY = 2.0
MAX_DELAY = 7.0
DELAY_INCREASE_ON_BLOCK = 1.5  # Multiply delay by this when blocked
MAX_DELAY_CAP = 30.0

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0  # Exponential backoff

# Pagination
MAX_PAGES_PER_SEARCH = 20  # Safety limit for endless pagination

# Output directory
OUTPUT_DIR = "output"

# Output file (same as before)
OUTPUT_FILE = "discovered_companies.json"

# Progress tracking
PROGRESS_FILE = "discovery_progress.json"

# Browser configuration
VISIBLE_MODE = True  # Set to False for headless
TIMEOUT = 30000  # 30 seconds page load timeout

# Google Search URL
GOOGLE_SEARCH_URL = "https://www.google.com/search"

# Block detection keywords
BLOCK_INDICATORS = [
    "unusual traffic",
    "captcha",
    "i'm not a robot",
    "verify you're human",
    "rate limit",
    "too many requests",
    "try again later",
    "automated queries",
]

# Selectors for Google results
RESULT_SELECTOR = "div[data-ved] h3 a, div.g h3 a, .yuRUbf a"
NEXT_PAGE_SELECTOR = (
    "a[aria-label='Next page'], a:has-text('Next'), td a:has-text('Next')"
)
NO_RESULTS_SELECTOR = "div[role='heading']:has-text('did not match')"
