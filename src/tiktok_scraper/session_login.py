#!/usr/bin/env python3
"""
TikTok session login - Open browser, let user manually log in, save cookies.
Usage: python session_login.py
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = Path(__file__).parent.parent / "tiktok_session_cookies.json"
TIKTOK_URL = "https://www.tiktok.com"

async def main():
    print("=== TikTok Session Login ===\n")
    print("This will open a browser window.")
    print("You have 90 seconds to log in to TikTok manually.")
    print("The script will automatically save cookies after 90 seconds.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(TIKTOK_URL)
        print(f"✓ Opened: {TIKTOK_URL}")
        print("\n⏳ LOG IN NOW - You have 90 seconds...")

        await asyncio.sleep(90)

        cookies = await context.cookies()

        COOKIES_FILE.write_text(json.dumps(cookies, indent=2))
        print(f"\n✓ Cookies saved to: {COOKIES_FILE}")
        print(f"  Total cookies: {len(cookies)}")

        await browser.close()

        print("\nSession ready for scraping!")

if __name__ == "__main__":
    asyncio.run(main())