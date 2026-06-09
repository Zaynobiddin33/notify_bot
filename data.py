from playwright.sync_api import sync_playwright
from playwright.sync_api import Error as PlaywrightError
from dotenv import load_dotenv
import os
import time

load_dotenv()

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")


def appointments_available() -> bool:
    if not EMAIL or not PASSWORD:
        raise RuntimeError("PRENOTAMI_EMAIL and PRENOTAMI_PASSWORD must be set")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()

        try:
            page.goto(
                "https://prenotami.esteri.it/",
                wait_until="domcontentloaded"
            )

            page.get_by_text(
                "Effettuare il Login per accedere al portale"
            ).click(timeout=60000)

            page.locator('input[type="text"]').fill(EMAIL)
            page.locator('input[type="password"]').fill(PASSWORD)

            page.locator('button[type="submit"]').click()

            page.wait_for_load_state("load")
            page.wait_for_timeout(5000)
            time.sleep(5)

            try:
                page.goto(
                    "https://prenotami.esteri.it/Services/Booking/6000",
                    wait_until="domcontentloaded",
                )
            except PlaywrightError as exc:
                if "net::ERR_ABORTED" not in str(exc):
                    raise

            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            content = page.content()
            final_res = []

            unavailable_text = (
                "Stante l'elevata richiesta i posti disponibili "
                "per il servizio scelto sono esauriti."
            )
            final_res.append(unavailable_text not in content)

            try:
                page.goto(
                    "https://prenotami.esteri.it/Services/Booking/6005",
                    wait_until="domcontentloaded",
                )
            except PlaywrightError as exc:
                if "net::ERR_ABORTED" not in str(exc):
                    raise

            page.wait_for_load_state("domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)

            content = page.content()

            unavailable_text = (
                "Stante l'elevata richiesta i posti disponibili "
                "per il servizio scelto sono esauriti."
            )
            final_res.append(unavailable_text not in content)

            return any(final_res)

        finally:
            browser.close()


if __name__ == "__main__":
    if appointments_available():
        print("APPOINTMENTS AVAILABLE!")
    else:
        print("No appointments available.")
