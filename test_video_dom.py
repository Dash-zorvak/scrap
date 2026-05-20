#!/usr/bin/env python3
import asyncio
import json
import re
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
    
    # Try to go to a video directly
    video_id = "7498410883728496959"
    username = "alcaldiasa"
    
    print(f"1. Loading video {video_id}...")
    await page.goto(f"https://www.tiktok.com/@{username}/video/{video_id}", timeout=30000)
    await asyncio.sleep(5)
    
    # Wait for page to be interactive
    print("2. Waiting for content...")
    await page.wait_for_load_state("networkidle", timeout=15000)
    await asyncio.sleep(3)
    
    # Try to extract data from the page using various methods
    print("3. Extracting data...")
    
    # Method 1: Check what's in the HTML
    content = await page.content()
    print(f"   Page length: {len(content)}")
    
    # Method 2: Look for any script with video data
    scripts = await page.query_selector_all("script")
    print(f"   Scripts: {len(scripts)}")
    
    # Method 3: Try to get data from the rendered page
    data = await page.evaluate("""
        () => {
            const result = {};
            
            // Try various selectors for description
            const descSelectors = [
                '[data-e2e="video-desc"]',
                '.tiktok-video-detail-desc',
                '[class*="desc"]',
                'h1[class*="title"]'
            ];
            
            for (const sel of descSelectors) {
                const el = document.querySelector(sel);
                if (el && el.textContent) {
                    result.description = el.textContent;
                    break;
                }
            }
            
            // Try selectors for stats
            const statsSelectors = [
                '[data-e2e="view-count"]',
                '[class*="viewCount"]',
                '[class*="view-count"]'
            ];
            
            for (const sel of statsSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    result.views = el.textContent;
                    break;
                }
            }
            
            // Try to get likes
            const likeSelectors = [
                '[data-e2e="like-count"]',
                '[class*="likeCount"]'
            ];
            
            for (const sel of likeSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    result.likes = el.textContent;
                    break;
                }
            }
            
            return result;
        }
    """)
    
    print(f"   Extracted: {json.dumps(data)}")
    
    # Method 4: Try to get any element with numeric content that looks like stats
    numeric_data = await page.evaluate("""
        () => {
            // Look for any element with class containing specific keywords
            const allElements = document.querySelectorAll('*');
            const results = [];
            
            allElements.forEach(el => {
                const className = el.className || '';
                const text = el.textContent || '';
                
                if ((className.includes('count') || className.includes('stat')) && text.match(/^[\d,]+$/)) {
                    results.push({class: className, text: text});
                }
            });
            
            return results.slice(0, 10);
        }
    """)
    
    print(f"   Numeric elements: {json.dumps(numeric_data)}")
    
    await browser.close()
    await p.stop()

asyncio.run(main())