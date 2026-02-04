from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright_stealth import stealth


def human_delay(min_seconds: float = 1.5, max_seconds: float = 3.5) -> float:
    return random.uniform(min_seconds, max_seconds)


class StealthBrowser:
    def __init__(self, headless: bool = True) -> None:
        self._headless = headless

    @asynccontextmanager
    async def session(self) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self._headless)
            context = await browser.new_context()
            page = await context.new_page()
            await stealth(page)
            try:
                yield browser, context, page
            finally:
                await context.close()
                await browser.close()

    async def wait_human(self, min_seconds: float = 1.5, max_seconds: float = 3.5) -> None:
        await asyncio.sleep(human_delay(min_seconds, max_seconds))
