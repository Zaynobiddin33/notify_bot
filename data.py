from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")
UNAVAILABLE_TEXT = (
    "Stante l'elevata richiesta i posti disponibili "
    "per il servizio scelto sono esauriti."
)
SERVICE_IDS = ("6000", "6005")


def goto_page(page, url: str) -> None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except PlaywrightError as exc:
        if "net::ERR_ABORTED" not in str(exc):
            raise

    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except (PlaywrightError, PlaywrightTimeoutError):
        pass


def page_text_sample(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)[:700]
    except PlaywrightError:
        return page.content()[:700]


def open_login_page(page) -> None:
    goto_page(page, "https://prenotami.esteri.it/")

    login_link = page.get_by_text("Effettuare il Login per accedere al portale")
    try:
        if login_link.is_visible(timeout=15000):
            login_link.click(timeout=15000)
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            return
    except (PlaywrightError, PlaywrightTimeoutError):
        pass

    goto_page(page, "https://prenotami.esteri.it/Account/Login")


def login(page) -> None:
    open_login_page(page)

    username_input = page.locator('input[type="email"], input[type="text"]').first
    password_input = page.locator('input[type="password"]').first

    try:
        username_input.wait_for(state="visible", timeout=30000)
        password_input.wait_for(state="visible", timeout=30000)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(
            "Prenotami login form was not found. "
            f"url={page.url!r} title={page.title()!r} body={page_text_sample(page)!r}"
        ) from exc

    username_input.fill(EMAIL)
    password_input.fill(PASSWORD)
    page.locator('button[type="submit"], input[type="submit"]').first.click()
    page.wait_for_load_state("load", timeout=60000)
    page.wait_for_timeout(5000)


def service_available(page, service_id: str) -> bool:
    goto_page(page, f"https://prenotami.esteri.it/Services/Booking/{service_id}")
    page.wait_for_timeout(3000)
    return UNAVAILABLE_TEXT not in page.content()


def appointments_available() -> bool:
    if not EMAIL or not PASSWORD:
        raise RuntimeError("PRENOTAMI_EMAIL and PRENOTAMI_PASSWORD must be set")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        try:
            login(page)
            return any(service_available(page, service_id) for service_id in SERVICE_IDS)
        finally:
            browser.close()


if __name__ == "__main__":
    if appointments_available():
        print("APPOINTMENTS AVAILABLE!")
    else:
        print("No appointments available.")
