import asyncio
import logging
from .browser_discovery import (
    discover_with_browser,
    save_discovered_companies,
    load_progress,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def run():
    print("Starting browser discovery...")
    results = await discover_with_browser()
    save_discovered_companies(results)

    # Print summary
    print("\n" + "=" * 60)
    print("DISCOVERY COMPLETE")
    print("=" * 60)
    total = 0
    for ats, companies in results.items():
        print(f"  {ats:12}: {len(companies):4} companies")
        total += len(companies)
    print(f"  {'TOTAL':12}: {total:4} companies")

    progress = load_progress()
    if progress["metadata"]["status"] == "complete":
        print("\n✅ Discovery is COMPLETE")
    elif progress["metadata"]["status"] == "blocked":
        print("\n⚠️  Discovery was BLOCKED - run again to resume")
    else:
        print("\n⏸️  Discovery PAUSED - run again to resume")


if __name__ == "__main__":
    asyncio.run(run())
