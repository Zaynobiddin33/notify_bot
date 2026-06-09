# /home/ubuntu/notify_visa_bot/notify_bot/data.py

import os
import sys
from dotenv import load_dotenv
from seleniumbase import SB

load_dotenv()

# Force the system PATH inside the script so Selenium can find /usr/bin/chromedriver
if "/usr/bin" not in os.environ["PATH"]:
    os.environ["PATH"] = "/usr/bin:" + os.environ["PATH"]

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")
LOCALE = os.getenv("PRENOTAMI_LOCALE", "it-IT")

SERVICE_IDS = ["6000", "6005"]
UNAVAILABLE_TEXT = "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."

def check_appointments():
    if not EMAIL or not PASSWORD:
        print("Error: EMAIL and PASSWORD environment variables must be set.")
        return False

    # Cleaned up arguments (removed executable_path)
    with SB(
        headless=HEADLESS, 
        locale_code=LOCALE, 
        binary_location="/usr/bin/chromium-browser",  # Points to ARM64 Chromium
        driver_version="custom"                       # Forces Selenium to use system PATH chromedriver
    ) as sb:
        
        # 1. Open home page & login
        sb.open("https://prenotami.esteri.it/")
        sb.wait_for_ready_state_complete(timeout=30)
        
        try:
            sb.click("#pingid-button", timeout=5)
        except Exception:
            sb.open("https://prenotami.esteri.it/Account/Login")
            
        sb.type('input[type="email"]', EMAIL)
        sb.type('input[type="password"]', PASSWORD)
        sb.click('button[type="submit"]')
        sb.sleep(5)
        
        # 2. Check the services
        any_available = False
        for service_id in SERVICE_IDS:
            sb.open(f"https://prenotami.esteri.it/Services/Booking/{service_id}")
            sb.sleep(3)
            
            if UNAVAILABLE_TEXT not in sb.get_page_source():
                print(f"🎉 APPOINTMENTS AVAILABLE for service {service_id}!")
                any_available = True
            else:
                print(f"No slots for service {service_id}.")
                
        return any_available