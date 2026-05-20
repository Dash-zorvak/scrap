#!/usr/bin/env python3
"""
TikTok Scraper usando playwright-stealth + API endpoint
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

OUTPUT_DIR = Path("outputs/tiktok")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def get_user_data(username: str):
    """Get user data and videos directly from page."""
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = await browser.new_context()
    page = await context.new_page()
    
    Stealth().apply_stealth_sync(page)
    
    print(f"Loading @{username}...")
    await page.goto(f"https://www.tiktok.com/@{username}", timeout=30000, wait_until="load")
    await asyncio.sleep(8)
    
    content = await page.content()
    
    sec_uid = None
    videos = []
    
    if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
        patterns = [
            r'__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.*?\})</script>',
            r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?"(\{.*?\})',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    default = data.get("__DEFAULT_SCOPE__", {})
                    user_detail = default.get("webapp.user-detail", {})
                    sec_uid = user_detail.get("userInfo", {}).get("user", {}).get("secUid")
                    
                    # Get videos directly from page data
                    videos = user_detail.get("awemeList", [])
                    print(f"   Videos in initial load: {len(videos)}")
                    
                    if sec_uid:
                        break
                except:
                    continue
    
    return sec_uid, videos, p, browser, page

async def fetch_videos_via_browser(page, sec_uid: str, cursor: int = 0, count: int = 35) -> dict:
    """Fetch videos using TikTok API through browser."""
    url = "https://www.tiktok.com/api/post/item_list/"
    params = {
        "aid": "1988",
        "count": str(count),
        "cursor": str(cursor),
        "device_platform": "web_pc",
        "secUid": sec_uid,
    }
    
    try:
        resp = await page.request.get(url, params=params)
        text = await resp.text()
        print(f"   API response length: {len(text)}")
        if text:
            return json.loads(text)
        return {"items": [], "has_more": False}
    except Exception as e:
        print(f"   API error: {e}")
        return {"items": [], "has_more": False}

def extract_video_data(video: dict) -> dict:
    """Extract video data."""
    desc = video.get("desc", "")
    stats = video.get("stats", {})
    
    return {
        "video_id": video.get("id"),
        "description": desc,
        "create_time": datetime.fromtimestamp(int(video.get("createTime", 0))).isoformat(),
        "views": stats.get("playCount"),
        "likes": stats.get("diggCount"),
        "comments": stats.get("commentCount"),
        "shares": stats.get("shareCount"),
        "saves": stats.get("collectCount"),
        "hashtags": re.findall(r'#(\w+)', desc),
        "mentions": re.findall(r'@(\w+)', desc),
    }

async def scroll_for_videos(page, max_scrolls: int = 10) -> list:
    """Scroll down to load more videos from profile."""
    all_videos = []
    seen_ids = set()
    
    for scroll_num in range(max_scrolls):
        # Get current videos from page
        videos = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('[data-e2e="user-post-item"]');
                const videos = [];
                items.forEach(item => {
                    const link = item.querySelector('a');
                    if (link && link.href) {
                        const id = link.href.split('/').pop();
                        videos.push({ id: id, element: item });
                    }
                });
                return videos;
            }
        """)
        
        for v in videos:
            if v['id'] not in seen_ids:
                seen_ids.add(v['id'])
                all_videos.append(v['id'])
        
        print(f"   Scroll {scroll_num + 1}: {len(all_videos)} videos loaded")
        
        # Scroll down
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(2)
    
    return all_videos

async def scrape(username: str, max_videos: int = None):
    print(f"\n=== TikTok Scraper: @{username} ===\n")
    
    print("1. Abriendo perfil...")
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    context = await browser.new_context()
    page = await context.new_page()
    
    Stealth().apply_stealth_sync(page)
    
    await page.goto(f"https://www.tiktok.com/@{username}", timeout=30000, wait_until="load")
    await asyncio.sleep(8)
    
    print(f"\n2. Extrayendo videos (scrolling + DOM)...")
    
    posts = []
    scroll_count = 0
    max_scrolls = (max_videos or 50) // 10 + 5
    
    while scroll_count < max_scrolls:
        scroll_count += 1
        
        # Extract video data from current visible elements
        video_data = await page.evaluate(f"""
            () => {{
                const items = document.querySelectorAll('[data-e2e="user-post-item"]');
                const videos = [];
                items.forEach(item => {{
                    try {{
                        // Get video info from element attributes or child elements
                        const link = item.querySelector('a');
                        const href = link ? link.href : '';
                        const id = href.split('/').pop();
                        
                        // Look for stats in the element
                        const text = item.textContent;
                        
                        // Extract numbers from text (views, likes, etc)
                        const viewsMatch = text.match(/([\\d,]+)\\s*(?:views|reproducciones)/i);
                        const likesMatch = text.match(/([\\d,]+)\\s*(?:likes|me gusta)/i);
                        
                        videos.push({{
                            id: id,
                            href: href
                        }});
                    }} catch(e) {{}}
                }});
                return videos;
            }}
        """)
        
        print(f"   Scroll {scroll_count}: {len(video_data)} videos en DOM")
        
        # Scroll down
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(2)
        
        # Check if we've reached enough videos
        if max_videos and len(posts) >= max_videos:
            break
        
        # Try to get data from the JSON in the page as we scroll
        content = await page.content()
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.*?\})</script>', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                default = data.get("__DEFAULT_SCOPE__", {})
                user_detail = default.get("webapp.user-detail", {})
                aweme_list = user_detail.get("awemeList", [])
                
                if aweme_list:
                    print(f"   Found {len(aweme_list)} videos in JSON!")
                    for v in aweme_list:
                        if v.get('id') not in [p.get('video_id') for p in posts]:
                            stats = v.get('stats', {})
                            post = {
                                "video_id": v.get('id'),
                                "description": v.get('desc', ''),
                                "create_time": datetime.fromtimestamp(int(v.get('createTime', 0))).isoformat() if v.get('createTime') else None,
                                "views": stats.get('playCount'),
                                "likes": stats.get('diggCount'),
                                "comments": stats.get('commentCount'),
                                "shares": stats.get('shareCount'),
                                "saves": stats.get('collectCount'),
                                "hashtags": re.findall(r'#(\w+)', v.get('desc', '')),
                                "mentions": re.findall(r'@(\w+)', v.get('desc', '')),
                            }
                            posts.append(post)
                    
                    print(f"   Total posts: {len(posts)}")
    
    print(f"\n3. Total extraídos: {len(posts)} videos")
    
    # Close browser
    await browser.close()
    await p.stop()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"tiktok_{username}_{timestamp}.json"
    
    output = {
        "username": username,
        "scraped_at": datetime.now().isoformat(),
        "total_posts": len(posts),
        "posts": posts
    }
    
    output_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"   ✓ Guardado: {output_file}")
    
    if posts:
        p = posts[0]
        print(f"\n4. Preview:")
        print(f"   ID: {p['video_id']}")
        print(f"   Desc: {p['description'][:60]}...")
        print(f"   Views: {p['views']}")
        print(f"   Likes: {p['likes']}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="alcaldiasa")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    asyncio.run(scrape(args.user, args.limit))