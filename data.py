import os
from dotenv import load_dotenv
from seleniumbase import SB

load_dotenv()

EMAIL = os.getenv("PRENOTAMI_EMAIL")
PASSWORD = os.getenv("PRENOTAMI_PASSWORD")
HEADLESS = os.getenv("PRENOTAMI_HEADLESS", "true").lower() in ("1", "true", "yes")
LOCALE = os.getenv("PRENOTAMI_LOCALE", "it-IT")

SERVICE_IDS = ["6000", "6005"]
UNAVAILABLE_TEXT = "Stante l'elevata richiesta i posti disponibili per il servizio scelto sono esauriti."

def check_appointments():
    if not EMAIL or not PASSWORD:
        print("Error: EMAIL and PASSWORD environment variables must be set.")
        return

    # Note: binary_path bypasses the ARM64/aarch64 error from your logs
    with SB(headless=HEADLESS, locale_code=LOCALE, binary_location="/usr/bin/chromium-browser", driver_version="custom", executable_path="/usr/bin/chromedriver") as sb:
        
        # 1. Open home page & login
        sb.open("https://prenotami.esteri.it/")
        sb.wait_for_ready_state_complete(timeout=30)
        
        # Try clicking the initial login button if it exists, otherwise fallback to login page
        try:
            sb.click("#pingid-button", timeout=5)
        except Exception:
            sb.open("https://prenotami.esteri.it/Account/Login")
            
        sb.type('input[type="text"]', EMAIL)
        sb.type('input[type="password"]', PASSWORD)
        sb.click('button[type="submit"]')
        sb.sleep(5) # Let the dashboard load
        
        # 2. Check the services
        any_available = False
        for service_id in SERVICE_IDS:
            sb.open(f"https://prenotami.esteri.it/Services/Booking/{service_id}")
            sb.sleep(3) # Wait for page contents to render
            
            if UNAVAILABLE_TEXT not in sb.get_page_source():
                print(f"🎉 APPOINTMENTS AVAILABLE for service {service_id}!")
                any_available = True
            else:
                print(f"No slots for service {service_id}.")
                
        return any_available

if __name__ == "__main__":
    check_appointments()