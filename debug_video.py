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
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        Stealth().apply_stealth_sync(page)
        
        # Go to a specific video
        video_id = "7498410883728496959"  # Example video ID
        username = "alcaldiasa"
        
        print(f"Loading video {video_id}...")
        await page.goto(f"https://www.tiktok.com/@{username}/video/{video_id}", timeout=30000, wait_until="load")
        await asyncio.sleep(3)
        
        # Wait for video to fully load
        await page.wait_for_selector("video", timeout=10000)
        print("Video element found")
        await asyncio.sleep(3)
        
        # Try extracting from DOM instead
        page_data = await page.evaluate("""
            () => {
                // Try to get data from various elements
                const result = {};
                
                // Description
                const descEl = document.querySelector('[data-e2e="video-desc"], .tiktok-video-detail-desc');
                result.description = descEl ? descEl.textContent : '';
                
                // Stats - look for view count, like count, etc
                const stats = {};
                const viewEl = document.querySelector('[data-e2e="view-count"], [class*="view"]');
                const likeEl = document.querySelector('[data-e2e="like-count"], [class*="like"]');
                const commentEl = document.querySelector('[data-e2e="comment-count"], [class*="comment"]');
                const shareEl = document.querySelector('[data-e2e="share-count"], [class*="share"]');
                
                result.stats = {
                    view: viewEl ? viewEl.textContent : 'not found',
                    like: likeEl ? likeEl.textContent : 'not found',
                    comment: commentEl ? commentEl.textContent : 'not found',
                    share: shareEl ? shareEl.textContent : 'not found'
                };
                
                // Video ID from URL
                result.videoUrl = window.location.href;
                
                return result;
            }
        """)
        print(f"Page data: {json.dumps(page_data, indent=2)}")
        
        # Try to get the JSON data
        content = await page.content()
        
        # Check for universal data
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            print("Found universal data")
            
            # Try different patterns
            patterns = [
                r'__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.*?\})</script>',
            ]
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                        print(f"Data keys: {list(data.keys())}")
                        
                        default = data.get("__DEFAULT_SCOPE__", {})
                        print(f"Default keys: {list(default.keys())}")
                        
                        if "webapp.video-detail" in default:
                            detail = default["webapp.video-detail"]
                            print(f"Detail keys: {list(detail.keys())}")
                            
                            if "videoInfo" in detail:
                                info = detail["videoInfo"]
                                print(f"VideoInfo: {json.dumps(info, indent=2)[:500]}")
                        else:
                            # Try other keys
                            for k, v in default.items():
                                if isinstance(v, dict):
                                    print(f"  {k} keys: {list(v.keys())}")
                    except Exception as e:
                        print(f"Error: {e}")
        else:
            print("No universal data found")
            print(f"Page length: {len(content)}")
            
        await browser.close()

asyncio.run(main())