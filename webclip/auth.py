from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright
from slugify import slugify

from webclip.config import default_profiles_dir

DEFAULT_LOGIN_URLS = {
    "vas3k": "https://vas3k.club/auth/login/",
}


def profile_dir_for_site(site: str) -> Path:
    slug = slugify(site) or site.lower()
    return default_profiles_dir() / slug


def resolve_login_url(site: str, override: str | None) -> str:
    if override:
        return override
    site_key = site.lower().strip()
    if site_key in DEFAULT_LOGIN_URLS:
        return DEFAULT_LOGIN_URLS[site_key]
    msg = f"Unknown site '{site}'. Provide --login-url explicitly."
    raise ValueError(msg)


def run_auth_session(site: str, login_url: str, profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(login_url, wait_until="domcontentloaded")
            input(
                f"Finish login for '{site}' in the opened browser, then press Enter to continue..."
            )
        finally:
            context.close()
