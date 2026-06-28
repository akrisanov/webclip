from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from playwright.async_api import async_playwright


async def render_pdf_bytes(html: str, resolve_dir: Path | None = None) -> bytes:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        temp_file: Path | None = None
        try:
            if resolve_dir is not None:
                working_dir = resolve_dir.expanduser().resolve()
                working_dir.mkdir(parents=True, exist_ok=True)
                temp_file = working_dir / f".webclip-pdf-{uuid4().hex}.html"
                temp_file.write_text(html, encoding="utf-8")
                await page.goto(temp_file.as_uri(), wait_until="networkidle")
            else:
                await page.set_content(html, wait_until="networkidle")
            pdf = await page.pdf(format="A4", print_background=True)
            return pdf
        finally:
            if temp_file is not None and temp_file.exists():
                temp_file.unlink()
            await context.close()
            await browser.close()
