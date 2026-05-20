#!/usr/bin/env python3
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        Stealth().apply_stealth_sync(page)
        
        print("Loading TikTok...")
        await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=30000, wait_until="load")
        await asyncio.sleep(8)
        
        content = await page.content()
        
        Path("tiktok_page.html").write_text(content)
        print(f"Saved page ({len(content)} chars)")
        
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?=.*?(\{.*?\});', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                Path("tiktok_data.json").write_text(json.dumps(data, indent=2))
                print(f"Saved JSON data")
                print(f"Keys: {list(data.keys())}")
                
                default = data.get("__DEFAULT_SCOPE__", {})
                user_detail = default.get("webapp.user-detail", {})
                user_info = user_detail.get("userInfo", {})
                user = user_info.get("user", {})
                print(f"secUid: {user.get('secUid', 'NOT FOUND')[:50]}")
        else:
            print("No __UNIVERSAL_DATA_FOR_REHYDRATION__ found")
            
        await browser.close()

asyncio.run(main())