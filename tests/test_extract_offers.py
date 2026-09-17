from unittest.mock import Mock

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from src import extract_offers
from src.utils import analyze_offers
from bs4 import BeautifulSoup


OFFER_HTML = """
<button>Tout accepter</button>
<h2>Unrelated heading</h2>
<div>
    <h2>Offres en cours</h2>
    <p>Du 14 au 18 septembre, 2€ offerts avec le code TESTCODE.</p>
    <h2>Offres de bienvenue</h2>
    <p>Welcome offer.</p>
</div>
"""


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, monkeypatch, tmp_path):
    monkeypatch.setattr(extract_offers, "URL", "https://refectory.test/offers")
    monkeypatch.setattr(extract_offers, "NAVIGATION_TIMEOUT_MS", 2000)
    monkeypatch.setattr(extract_offers, "CONTENT_TIMEOUT_MS", 500)
    monkeypatch.setattr(extract_offers, "DIAGNOSTICS_DIR", tmp_path)
    monkeypatch.setattr(extract_offers.time, "sleep", Mock())
    page = browser.new_page()
    # All browser requests are intercepted; these tests never contact Refectory.
    page.route("**/*", lambda route: route.fulfill(body=OFFER_HTML, content_type="text/html"))
    yield page
    page.close()


@pytest.mark.parametrize("html", [
    "<h2>Unrelated heading</h2><p>Not an offer.</p>",
    "<h2>Offres de bienvenue</h2><p>Not a current offer.</p>",
    "<h2>Offres en cours</h2>",
    "<h2>Offres en cours</h2><p> </p>",
])
def test_incomplete_offers_content_is_not_ready(page, html):
    page.set_content(html)
    with pytest.raises(PlaywrightTimeoutError):
        extract_offers.wait_for_offers(page)


def test_waits_for_delayed_heading_and_offer_text(page, monkeypatch):
    monkeypatch.setattr(extract_offers, "CONTENT_TIMEOUT_MS", 2000)
    page.set_content("<h2>Unrelated heading</h2><div id='offers'></div>")
    page.evaluate("""() => {
        setTimeout(() => {
            document.querySelector('#offers').innerHTML = '<h2>Offres en cours</h2><p></p>';
            setTimeout(() => {
                document.querySelector('#offers p').textContent = 'Du 14 au 18 septembre';
            }, 150);
        }, 150);
    }""")

    extract_offers.wait_for_offers(page)

    assert page.locator("#offers p").inner_text() == "Du 14 au 18 septembre"


def test_empty_current_offers_section_is_valid(page):
    page.set_content("""
        <div><h2>Offres en cours</h2><p> </p>
        <h2>Offres de bienvenue</h2><p>Welcome offer.</p></div>
    """)

    extract_offers.wait_for_offers(page)

    soup = BeautifulSoup(page.content(), "html.parser")
    assert analyze_offers(soup.div.get_text("\n", strip=True)) == []


def test_export_does_not_wait_for_background_network_activity(page):
    pending_requests = []
    page.route("**/analytics", lambda route: pending_requests.append(route))
    page.route(
        extract_offers.URL,
        lambda route: route.fulfill(
            content_type="text/html",
            body=OFFER_HTML + "<script>fetch('/analytics')</script>",
        ),
    )

    html = extract_offers.load_offers_html(page)

    assert "TESTCODE" in html
    assert pending_requests
    # The old readiness criterion still fails for this otherwise usable page.
    with pytest.raises(PlaywrightTimeoutError):
        page.wait_for_load_state("networkidle", timeout=600)


@pytest.mark.parametrize("failure", ["navigation", "content", "http"])
def test_transient_failure_is_retried(page, monkeypatch, failure):
    navigate = page.goto
    calls = []

    def flaky_goto(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            if failure == "navigation":
                raise PlaywrightTimeoutError("Temporary navigation timeout")
            page.route(
                extract_offers.URL,
                lambda route: route.fulfill(
                    status=503 if failure == "http" else 200,
                    content_type="text/html",
                    body="<button>Tout accepter</button><h2>Offres en cours</h2>",
                ),
                times=1,
            )
        return navigate(*args, **kwargs)

    monkeypatch.setattr(page, "goto", flaky_goto)

    assert "TESTCODE" in extract_offers.load_offers_html(page)
    assert len(calls) == 2
    extract_offers.time.sleep.assert_called_once_with(2)


@pytest.mark.parametrize("broken_screenshot", [False, True])
def test_exhausted_retries_save_diagnostics_and_preserve_error(
    page, monkeypatch, tmp_path, broken_screenshot
):
    original_error = PlaywrightTimeoutError("Navigation remains unavailable")
    navigate = Mock(side_effect=original_error)
    monkeypatch.setattr(page, "goto", navigate)
    if broken_screenshot:
        monkeypatch.setattr(
            page, "screenshot", Mock(side_effect=PlaywrightError("Screenshot failed"))
        )

    with pytest.raises(PlaywrightTimeoutError) as caught:
        extract_offers.load_offers_html(page)

    assert caught.value is original_error
    assert navigate.call_count == 3
    diagnostic = (tmp_path / "failure.txt").read_text(encoding="utf-8")
    assert "Navigation remains unavailable" in diagnostic
    assert "Final URL: about:blank" in diagnostic
    assert "HTTP status: unknown" in diagnostic
    assert (tmp_path / "failure.html").is_file()
    assert (tmp_path / "failure.png").is_file() is not broken_screenshot


def test_http_failure_is_reported_without_parsing_error_page(page, tmp_path):
    page.route(
        extract_offers.URL,
        lambda route: route.fulfill(status=503, body="Service unavailable"),
    )

    with pytest.raises(RuntimeError, match="HTTP 503"):
        extract_offers.load_offers_html(page)

    assert "HTTP status: 503" in (tmp_path / "failure.txt").read_text(encoding="utf-8")


def test_browser_is_closed_when_extraction_fails(monkeypatch):
    playwright_context = Mock()
    playwright = Mock()
    playwright_context.__enter__ = Mock(return_value=playwright)
    playwright_context.__exit__ = Mock(return_value=False)
    browser = playwright.chromium.launch.return_value
    monkeypatch.setattr(extract_offers, "sync_playwright", lambda: playwright_context)
    monkeypatch.setattr(
        extract_offers, "load_offers_html", Mock(side_effect=PlaywrightTimeoutError("Failed"))
    )
    notify = Mock()
    monkeypatch.setattr(extract_offers, "filter_and_notify", notify)

    with pytest.raises(PlaywrightTimeoutError):
        extract_offers.main()

    browser.close.assert_called_once()
    notify.assert_not_called()
