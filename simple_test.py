#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def main():
    print("1. Starting playwright...")
    async with async_playwright() as p:
        print("2. Launching browser (headless)...")
        browser = await p.chromium.launch(headless=True)
        print("3. Creating page...")
        page = await browser.new_page()
        print("4. Loading example.com...")
        await page.goto("https://example.com")
        print(f"5. Title: {await page.title()}")
        print("6. Done!")
        await browser.close()

print("Running...")
asyncio.run(main())