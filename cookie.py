from seleniumbase import SB
import json

with SB() as sb:
    sb.open("https://prenotami.esteri.it")

    input("Press Enter...")

    with open("cookies.json", "w") as f:
        json.dump(sb.driver.get_cookies(), f)