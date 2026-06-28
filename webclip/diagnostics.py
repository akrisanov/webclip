from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from webclip.config import default_config_path, default_profiles_dir


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    details: str


def run_doctor(vault: Path | None = None) -> list[CheckResult]:
    results = [
        _check_python_version(),
        _check_config_path_parent(),
        _check_profiles_dir(),
        _check_playwright_chromium(),
    ]
    if vault is not None:
        results.append(_check_vault(vault))
    return results


def _check_python_version() -> CheckResult:
    major, minor = sys.version_info.major, sys.version_info.minor
    ok = (major, minor) >= (3, 14)
    return CheckResult(
        name="Python version",
        ok=ok,
        details=f"{major}.{minor} ({'supported' if ok else 'requires >= 3.14'})",
    )


def _check_config_path_parent() -> CheckResult:
    config_parent = default_config_path().parent
    try:
        config_parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return CheckResult(
            name="Config directory",
            ok=False,
            details=f"Cannot create {config_parent}: {error}",
        )
    writable = os.access(config_parent, os.W_OK)
    return CheckResult(
        name="Config directory",
        ok=writable,
        details=f"{config_parent} ({'writable' if writable else 'not writable'})",
    )


def _check_profiles_dir() -> CheckResult:
    profiles_dir = default_profiles_dir()
    try:
        profiles_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return CheckResult(
            name="Profiles directory",
            ok=False,
            details=f"Cannot create {profiles_dir}: {error}",
        )
    writable = os.access(profiles_dir, os.W_OK)
    return CheckResult(
        name="Profiles directory",
        ok=writable,
        details=f"{profiles_dir} ({'writable' if writable else 'not writable'})",
    )


def _check_playwright_chromium() -> CheckResult:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except PlaywrightError as error:
        return CheckResult(
            name="Playwright Chromium",
            ok=False,
            details=f"Unavailable: {error}. Run: uv run playwright install chromium",
        )
    return CheckResult(name="Playwright Chromium", ok=True, details="Available")


def _check_vault(vault: Path) -> CheckResult:
    vault_path = vault.expanduser()
    if not vault_path.exists():
        return CheckResult(name="Vault path", ok=False, details=f"{vault_path} does not exist")
    if not vault_path.is_dir():
        return CheckResult(name="Vault path", ok=False, details=f"{vault_path} is not a directory")
    writable = os.access(vault_path, os.W_OK)
    return CheckResult(
        name="Vault path",
        ok=writable,
        details=f"{vault_path} ({'writable' if writable else 'not writable'})",
    )
