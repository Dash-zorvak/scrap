#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    print("1. Starting playwright-stealth...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        stealth = Stealth()
        stealth.apply_stealth_sync(page)
        
        print("2. Loading TikTok...")
        await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=20000)
        print(f"3. URL: {page.url}")
        print(f"   Title: {await page.title()}")
        
        await browser.close()
        print("4. Done")

asyncio.run(main())