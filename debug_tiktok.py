#!/usr/bin/env python3
import asyncio
import json
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    print("Starting...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        Stealth().apply_stealth_sync(page)
        
        print("Loading TikTok...")
        response = await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=30000, wait_until="load")
        print(f"Response: {response.status}")
        
        await asyncio.sleep(8)
        
        content = await page.content()
        print(f"Length: {len(content)}")
        
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?=.*?(\{.*?\});', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                print(f"Keys: {list(data.keys())}")
                
                default = data.get("__DEFAULT_SCOPE__", {})
                print(f"Default keys: {list(default.keys())}")
                
                user_detail = default.get("webapp.user-detail", {})
                print(f"User detail keys: {list(user_detail.keys())}")
                
                user_info = user_detail.get("userInfo", {})
                print(f"UserInfo keys: {list(user_info.keys())}")
                
                if "user" in user_info:
                    user = user_info["user"]
                    sec_uid = user.get("secUid")
                    if sec_uid:
                        print(f"SUCCESS! secUid: {sec_uid[:30]}...")
                    else:
                        print("secUid not in user")
                        print(f"User keys: {list(user.keys())}")
        else:
            print("No universal data found")
            # Check what we have
            scripts = await page.query_selector_all("script")
            print(f"Scripts: {len(scripts)}")
            
        await browser.close()
        print("Done!")

asyncio.run(main())