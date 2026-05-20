#!/usr/bin/env python3
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    print("1. Starting with Firefox...")
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        print("2. Browser launched")
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        print("3. Loading TikTok...")
        
        try:
            await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=15000)
            print(f"4. Loaded! URL: {page.url}")
            print(f"   Title: {await page.title()}")
        except Exception as e:
            print(f"4. Error: {e}")
        
        await browser.close()
        print("5. Done")

asyncio.run(main())