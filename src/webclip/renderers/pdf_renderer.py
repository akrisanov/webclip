from __future__ import annotations

from playwright.async_api import async_playwright


async def render_pdf_bytes(html: str) -> bytes:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf = await page.pdf(format="A4", print_background=True)
        await context.close()
        await browser.close()
        return pdf
