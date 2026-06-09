from dotenv import load_dotenv
from seleniumbase import SB
import os

load_dotenv()

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")
LOCALE = os.getenv("PRENOTAMI_LOCALE", "it-IT")
SCREENSHOT_PATH = os.getenv("PRENOTAMI_SCREENSHOT_PATH", "prenotami-entry.png")
UNAVAILABLE_TEXT = (
    "Stante l'elevata richiesta i posti disponibili "
    "per il servizio scelto sono esauriti."
)
SERVICE_IDS = ("6000", "6005")
LIMITED_ACCESS_TEXTS = (
    "Accesso temporaneamente limitato",
    "Verifica CAPTCHA",
    "Sono un essere umano",
    "potenzialmente automatizzato",
)


class AccessTemporarilyLimited(RuntimeError):
    pass


def save_screenshot(sb, path: str) -> None:
    if not path:
        return

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    sb.save_screenshot(path)


def page_text_sample(sb) -> str:
    try:
        return sb.get_text("body")[:700]
    except Exception:
        return sb.get_page_source()[:700]


def ensure_not_limited(sb) -> None:
    body = page_text_sample(sb)
    if any(text in body for text in LIMITED_ACCESS_TEXTS):
        raise AccessTemporarilyLimited(
            "Prenotami temporarily limited access and requested CAPTCHA. "
            f"url={sb.get_current_url()!r} body={body!r}"
        )


def open_page(sb, url: str) -> None:
    sb.open(url)
    sb.wait_for_ready_state_complete(timeout=60)


def open_login_page(sb) -> None:
    open_page(sb, "https://prenotami.esteri.it/")
    save_screenshot(sb, SCREENSHOT_PATH)
    ensure_not_limited(sb)

    login_url = None
    try:
        sb.wait_for_element_visible("#pingid-button", timeout=15)
        login_url = sb.get_attribute("#pingid-button", "href")
        sb.click("#pingid-button")
        sb.wait_for_ready_state_complete(timeout=30)
        return
    except Exception:
        if login_url:
            open_page(sb, login_url)
            return

    open_page(sb, "https://prenotami.esteri.it/Account/Login")


def login(sb) -> None:
    open_login_page(sb)
    ensure_not_limited(sb)

    username_selector = 'input[type="email"], input[type="text"]'
    password_selector = 'input[type="password"]'

    try:
        sb.wait_for_element_visible(username_selector, timeout=30)
        sb.wait_for_element_visible(password_selector, timeout=30)
    except Exception as exc:
        raise RuntimeError(
            "Prenotami login form was not found. "
            f"url={sb.get_current_url()!r} body={page_text_sample(sb)!r}"
        ) from exc

    sb.type(username_selector, EMAIL)
    sb.type(password_selector, PASSWORD)
    sb.click('button[type="submit"], input[type="submit"]')
    sb.wait_for_ready_state_complete(timeout=60)
    sb.sleep(5)
    ensure_not_limited(sb)


def service_available(sb, service_id: str) -> bool:
    open_page(sb, f"https://prenotami.esteri.it/Services/Booking/{service_id}")
    sb.sleep(3)
    ensure_not_limited(sb)
    return UNAVAILABLE_TEXT not in sb.get_page_source()


def appointments_available() -> bool:
    if not EMAIL or not PASSWORD:
        raise RuntimeError("PRENOTAMI_EMAIL and PRENOTAMI_PASSWORD must be set")

    with SB(headless=HEADLESS, locale_code=LOCALE) as sb:
        login(sb)
        return any(service_available(sb, service_id) for service_id in SERVICE_IDS)


if __name__ == "__main__":
    if appointments_available():
        print("APPOINTMENTS AVAILABLE!")
    else:
        print("No appointments available.")
