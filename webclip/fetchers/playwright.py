from __future__ import annotations

from pathlib import Path

from playwright.async_api import async_playwright

from webclip.fetchers.base import FetchRequest, FetchResult


class PlaywrightFetcher:
    name = "browser"

    def __init__(self, profile_dir: Path | None = None, headless: bool = True) -> None:
        self._profile_dir = profile_dir
        self._headless = headless

    async def fetch(self, request: FetchRequest) -> FetchResult:
        async with async_playwright() as playwright:
            if self._profile_dir is not None:
                self._profile_dir.mkdir(parents=True, exist_ok=True)
                context = await playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self._profile_dir),
                    headless=self._headless,
                )
                page = context.pages[0] if context.pages else await context.new_page()
                response = await page.goto(request.url, wait_until="networkidle")
                html = await page.content()
                final_url = page.url
                status_code = response.status if response is not None else 200
                await context.close()
                return FetchResult(
                    url=request.url,
                    final_url=final_url,
                    status_code=status_code,
                    html=html,
                )

            browser = await playwright.chromium.launch(headless=self._headless)
            context = await browser.new_context()
            page = await context.new_page()
            response = await page.goto(request.url, wait_until="networkidle")
            html = await page.content()
            final_url = page.url
            status_code = response.status if response is not None else 200
            await context.close()
            await browser.close()
            return FetchResult(
                url=request.url,
                final_url=final_url,
                status_code=status_code,
                html=html,
            )
