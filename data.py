import json
import os

from dotenv import load_dotenv
from seleniumbase import SB

load_dotenv()

if "/usr/bin" not in os.environ["PATH"]:
    os.environ["PATH"] = "/usr/bin:" + os.environ["PATH"]

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")
LOCALE = os.getenv("PRENOTAMI_LOCALE", "it-IT")

UNAVAILABLE_TEXT = "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."
COOKIES_PATH = os.getenv("PRENOTAMI_COOKIES_PATH", "cookies.json")


def require_credentials() -> tuple[str, str]:
    if not EMAIL or not PASSWORD:
        raise RuntimeError(
            "Missing PRENOTAMI_EMAIL or PRENOTAMI_PASSWORD. "
            "Add them to .env or export them before running data.py."
        )
    return EMAIL, PASSWORD


def load_cookies(sb) -> None:
    if not os.path.exists(COOKIES_PATH):
        return

    with open(COOKIES_PATH, encoding="utf-8") as cookies_file:
        cookies = json.load(cookies_file)

    for cookie in cookies:
        try:
            sb.driver.add_cookie(cookie)
        except Exception as exc:
            print(exc)


def check_appointments():
    email, password = require_credentials()

    with SB(headless=True, locale_code=LOCALE, uc=True) as sb:
        # sb.activate_cdp_mode('https://prenotami.esteri.it/')
        sb.open("https://prenotami.esteri.it/")
        load_cookies(sb)

        sb.click_captcha()

        sb.click("#pingid-button", timeout=5)
    
        sb.wait_for_element('#floatingLabelInput33')

        sb.type('input[type="text"]', email)
        sb.type('input[type="password"]', password)
        sb.click('button[type="submit"]')
        sb.wait_for_element("#advanced")

        any_available = False
        sb.open(f"https://prenotami.esteri.it/Services/Booking/6000")
        if UNAVAILABLE_TEXT not in sb.get_page_source():
            print(f"🎉 APPOINTMENTS AVAILABLE for service VISA!")
            any_available = True
        else:
            print(f"No slots for service VISA.")
        
        sb.sleep(3)

        sb.open(f"https://prenotami.esteri.it/Services/Booking/6005")
        if UNAVAILABLE_TEXT not in sb.get_page_source():
            print(f"🎉 APPOINTMENTS AVAILABLE for service DOI!")
            any_available = True
        else:
            print(f"No slots for service DOI.")

        return any_available


if __name__ == "__main__":
    check_appointments()
