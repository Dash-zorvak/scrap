#!/usr/bin/env python3
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

COOKIES_FILE = Path("src/tiktok_session_cookies.json")

async def main():
    print("Starting test...")
    
    cookies = json.loads(COOKIES_FILE.read_text())
    print(f"Cookies: {len(cookies)}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        print("Loading TikTok...")
        
        await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=30000)
        await asyncio.sleep(15)
        
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")
        
        content = await page.content()
        print(f"Content length: {len(content)}")
        
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            print("FOUND DATA!")
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?=.*?(\{.*?\});', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                print(f"Keys: {list(data.keys())}")
        else:
            print("NO DATA")
            
        await browser.close()

asyncio.run(main())