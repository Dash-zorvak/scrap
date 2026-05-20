#!/usr/bin/env python3
import asyncio
import json
import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        Stealth().apply_stealth_sync(page)
        
        print("Loading profile...")
        await page.goto("https://www.tiktok.com/@alcaldiasa", timeout=30000, wait_until="load")
        await asyncio.sleep(8)
        
        content = await page.content()
        
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.*?\})</script>', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                default = data.get("__DEFAULT_SCOPE__", {})
                user_detail = default.get("webapp.user-detail", {})
                
                aweme_list = user_detail.get("awemeList", [])
                print(f"Aweme list: {len(aweme_list)} videos")
                
                if aweme_list:
                    # Show what fields are available
                    first_video = aweme_list[0]
                    print(f"\nFirst video keys: {list(first_video.keys())}")
                    
                    stats = first_video.get("stats", {})
                    print(f"Stats keys: {list(stats.keys())}")
                    
                    print(f"\nSample video data:")
                    print(f"  id: {first_video.get('id')}")
                    print(f"  desc: {first_video.get('desc', '')[:80]}...")
                    print(f"  createTime: {first_video.get('createTime')}")
                    print(f"  playCount: {stats.get('playCount')}")
                    print(f"  diggCount: {stats.get('diggCount')}")
                    print(f"  commentCount: {stats.get('commentCount')}")
                    print(f"  shareCount: {stats.get('shareCount')}")
                    print(f"  collectCount: {stats.get('collectCount')}")
        
        # Now scroll and see if we can get more
        print("\nScrolling...")
        for i in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(2)
            
        # Check if there's new data
        content2 = await page.content()
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content2:
            match2 = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.*?\})</script>', content2, re.DOTALL)
            if match2:
                data2 = json.loads(match2.group(1))
                default2 = data2.get("__DEFAULT_SCOPE__", {})
                user_detail2 = default2.get("webapp.user-detail", {})
                aweme_list2 = user_detail2.get("awemeList", [])
                print(f"\nAfter scrolling: {len(aweme_list2)} videos")
        
        await browser.close()

asyncio.run(main())