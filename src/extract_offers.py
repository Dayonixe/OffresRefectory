from pathlib import Path
import re
import time

from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)
from bs4 import BeautifulSoup
from .utils import (analyze_offers, filter_and_notify)

URL = "https://www.refectory.fr/conditions-des-offres-en-cours"
MAX_ATTEMPTS = 3
NAVIGATION_TIMEOUT_MS = 60000
CONTENT_TIMEOUT_MS = 20000
DIAGNOSTICS_DIR = Path("artifacts/extract-offers")


def wait_for_offers(page):
    heading = page.locator("h2").filter(
        has_text=re.compile(r"^\s*Offres en cours\s*$")
    ).first
    heading.wait_for(state="visible", timeout=CONTENT_TIMEOUT_MS)

    # The heading alone can appear before the offer paragraphs. An immediately
    # following section also permits a legitimately empty current-offers section.
    heading.locator(
        "xpath=following-sibling::*[self::p or self::h2][normalize-space()][1]"
    ).wait_for(state="visible", timeout=CONTENT_TIMEOUT_MS)


def save_failure_diagnostics(page, status, error):
    # Diagnostics must never replace the original navigation/content error.
    try:
        DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
        (DIAGNOSTICS_DIR / "failure.txt").write_text(
            f"Requested URL: {URL}\nFinal URL: {page.url}\n"
            f"HTTP status: {status}\nError: {error}\n",
            encoding="utf-8",
        )
    except Exception as diagnostic_error:
        print(f"⚠️ Unable to save diagnostics: {diagnostic_error}", flush=True)
        return

    # Save these independently: a failed screenshot must not prevent HTML capture.
    try:
        (DIAGNOSTICS_DIR / "failure.html").write_text(
            page.content(), encoding="utf-8"
        )
    except Exception as diagnostic_error:
        print(f"⚠️ Unable to save HTML: {diagnostic_error}", flush=True)
    try:
        page.screenshot(path=str(DIAGNOSTICS_DIR / "failure.png"), timeout=5000)
    except Exception as diagnostic_error:
        print(f"⚠️ Unable to save screenshot: {diagnostic_error}", flush=True)


def load_offers_html(page):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        status = "unknown (navigation did not return a response)"
        try:
            print(f"🔍 Loading page... (attempt {attempt}/{MAX_ATTEMPTS})", flush=True)
            response = page.goto(
                URL, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT_MS
            )
            if response is not None:
                status = response.status
            print(f"🔍 HTTP {status} — URL: {page.url}", flush=True)
            if response is not None and not response.ok:
                raise RuntimeError(f"Offers page returned HTTP {status}")

            try:
                page.locator("text=Tout accepter").first.click(timeout=5000)
                print("✅ Cookies accepted", flush=True)
            except PlaywrightTimeoutError:
                print("🔍 No cookie banner detected", flush=True)

            print("🔍 Waiting for offers content to load...", flush=True)
            wait_for_offers(page)
            return page.content()
        except (PlaywrightError, RuntimeError) as error:
            print(
                f"⚠️ Loading failed (attempt {attempt}/{MAX_ATTEMPTS}): {error}\n"
                f"URL: {page.url} — HTTP status: {status}",
                flush=True,
            )
            if attempt == MAX_ATTEMPTS:
                save_failure_diagnostics(page, status, error)
                raise
            time.sleep(2 * attempt)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            html = load_offers_html(browser.new_page())
        finally:
            browser.close()

    # Extraction via BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Find the section containing the offers
    offers_block = next(
        (heading for heading in soup.find_all("h2")
         if heading.get_text(" ", strip=True) == "Offres en cours"),
        None,
    )
    if not offers_block:
        raise RuntimeError("Unable to find the 'Offres en cours' section")

    container = offers_block.find_parent()
    text = container.get_text("\n", strip=True)

    offers = analyze_offers(text)

    for o in offers:
        print("\n--- OFFER ---")
        for k, v in o.items():
            print(f"{k}: {v}")

    try:
        filter_and_notify(offers)
    except Exception as e:
        print(f"⚠️ Notification error: {e}")

if __name__ == "__main__":
    main()
