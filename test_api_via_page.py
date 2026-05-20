#!/usr/bin/env python3
import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = await browser.new_context()
    page = await context.new_page()
    
    Stealth().apply_stealth_sync(page)
    
    # First load the profile to establish session
    print("1. Loading profile...")
    await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=30000, wait_until="load")
    await asyncio.sleep(5)
    
    # Now try to fetch the API directly using page route interception
    print("2. Interception test...")
    
    sec_uid = "MS4wLjABAAAA512y-9TTmvycymky4XGY0gM8FEmK2J0-9qK7xT0pZ3kU"  # example
    
    # Try direct fetch
    api_url = f"https://www.tiktok.com/api/post/item_list/?aid=1988&count=20&cursor=0&device_platform=web_pc&secUid={sec_uid}"
    
    print(f"3. Fetching API: {api_url[:80]}...")
    
    resp = await page.request.get(api_url)
    print(f"   Status: {resp.status}")
    text = await resp.text()
    print(f"   Length: {len(text)}")
    print(f"   Preview: {text[:200]}")
    
    await browser.close()
    await p.stop()

asyncio.run(main())