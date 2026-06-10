
import os
import sys
from dotenv import load_dotenv
from seleniumbase import SB

if "/usr/bin" not in os.environ["PATH"]:
    os.environ["PATH"] = "/usr/bin:" + os.environ["PATH"]

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")
LOCALE = os.getenv("PRENOTAMI_LOCALE", "it-IT")

UNAVAILABLE_TEXT = "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."

def check_appointments():
    with SB( headless=True, uc=True) as sb:
        sb.open("https://prenotami.esteri.it/")
        sb.save_screenshot('new.png')
        sb.uc_gui_click_captcha()
        sb.save_screenshot('new2.png')
        sb.click("#pingid-button", timeout=5)

        sb.type('input[type="text"]', EMAIL)
        sb.type('input[type="password"]', PASSWORD)
        sb.click('button[type="submit"]')
        any_available = False
        sb.open(f"https://prenotami.esteri.it/Services/Booking/6000")
        if UNAVAILABLE_TEXT not in sb.get_page_source():
            print(f"🎉 APPOINTMENTS AVAILABLE for service VISA!")
            any_available = True
        else:
            print(f"No slots for service VISA.")

        sb.open(f"https://prenotami.esteri.it/Services/Booking/6005")
        if UNAVAILABLE_TEXT not in sb.get_page_source():
            print(f"🎉 APPOINTMENTS AVAILABLE for service DOI!")
            any_available = True
        else:
            print(f"No slots for service DOI.")

        return any_available
        
        
