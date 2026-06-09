"""
Helper: export Facebook cookies from Playwright browser.
Opens a browser window, lets you log into Facebook manually,
then saves cookies to data/facebook_cookies.json for use by deep-scraper.
"""
import json
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

COOKIES_PATH = os.path.join(os.path.dirname(__file__), "facebook_cookies.json")

from playwright.sync_api import sync_playwright

print("=" * 60)
print("EXPORTAR COOKIES DE FACEBOOK")
print("=" * 60)
print(f"\n1. Se abrió una ventana del navegador")
print(f"2. Iniciá sesión en Facebook MANUALMENTE")
print(f"3. La ventana se cerrará automáticamente 5s después de detectar login")
print(f"4. O esperá 120s si no hay login y se cierra sola")
print(f"\nCookies se guardarán en: {COOKIES_PATH}")
print("=" * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.facebook.com", timeout=60000)

    # Wait for login to complete (check cookies periodically)
    required = {"c_user", "xs"}
    for i in range(120):
        time.sleep(1)
        cookies = context.cookies()
        cookie_names = {c["name"] for c in cookies}
        if required.issubset(cookie_names):
            print(f"\n✅ Login detectado después de {i+1}s")
            break
    else:
        print(f"\n⏱ Tiempo máximo alcanzado. Guardando cookies actuales...")

    cookies = context.cookies()
    with open(COOKIES_PATH, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"✅ {len(cookies)} cookies guardadas en {COOKIES_PATH}")

    cookie_names = {c["name"] for c in cookies}
    if required.issubset(cookie_names):
        print("✅ Cookies de sesión válidas (c_user + xs presentes)")
    else:
        print("⚠️ Faltan cookies de sesión. Asegurate de estar logueado.")
        missing = required - cookie_names
        print(f"   Faltan: {missing}")

    browser.close()

print("\nAhora podés ejecutar el deep-scraper con:")
print(f"  ./scrapeo deep-scrape --page-url https://www.facebook.com/JoseMariaChicas --cookies-file {COOKIES_PATH} --max 500 --headless")
