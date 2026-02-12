import requests
import re
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import get_settings

settings = get_settings()


def harvest_companies_from_github():
    # URL for the raw markdown of the Summer 2026 Internships repo
    intern_url = settings.simplify_jobs_intern_url

    # Optional: New Grad 2026 repo often has different companies
    new_grad_url = settings.simplify_jobs_new_grad_url

    urls = [intern_url, new_grad_url]
    all_content = ""

    print(f"Fetching data from GitHub (2026 Cycle)...")

    for url in urls:
        try:
            print(f"  - GET {url}...")
            response = requests.get(url)
            if response.status_code == 200:
                all_content += response.text
            else:
                print(f"    [!] Failed {url} (Status: {response.status_code})")
        except Exception as e:
            print(f"    [!] Error fetching {url}: {e}")

    if not all_content:
        print("No content fetched. Exiting.")
        return set(), set()

    # Regex to find Lever and Greenhouse links
    # Captures the slug: jobs.lever.co/SLUG or boards.greenhouse.io/SLUG
    lever_pattern = r"jobs\.lever\.co/([a-zA-Z0-9\-\_]+)"
    gh_pattern = r"boards\.greenhouse\.io/([a-zA-Z0-9\-\_]+)"

    lever_slugs = set(re.findall(lever_pattern, all_content))
    gh_slugs = set(re.findall(gh_pattern, all_content))

    # Clean up common false positives
    ignore_list = {"jobs", "apply", "careers", "engineering", "people", "team", "internal"}
    lever_slugs = {s for s in lever_slugs if s.lower() not in ignore_list}
    gh_slugs = {s for s in gh_slugs if s.lower() not in ignore_list}

    print("\n--- RESULTS ---")
    print(f"Found {len(lever_slugs)} unique Lever companies")
    print(f"Found {len(gh_slugs)} unique Greenhouse companies")

    print("\n--- LEVER SAMPLE ---")
    print(list(lever_slugs)[:5])

    print("\n--- GREENHOUSE SAMPLE ---")
    print(list(gh_slugs)[:5])

    return lever_slugs, gh_slugs


if __name__ == "__main__":
    harvest_companies_from_github()
