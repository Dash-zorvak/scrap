#!/usr/bin/env python3
"""
TikTok Scraper usando endpoint api/post/item_list
No requiere autenticación - obtiene videos de cuentas públicas.

Usage: 
    python api_scraper.py                    # Scrapear @alcaldiasa (default)
    python api_scraper.py --user nombre     # Otro usuario
    python api_scraper.py --limit 100       # Limitar videos
"""
import asyncio
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import requests

# Add imports for NLP analysis
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona, extract_problematicas

OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "tiktok"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_USER = "alcaldiasa"

async def get_secuid_with_playwright(username: str) -> str:
    """Use Playwright to get secUid from TikTok profile page."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Loading profile: @{username}")
        
        try:
            await page.goto(f"https://www.tiktok.com/@{username}", timeout=60000, wait_until="domcontentloaded")
            print("   Page loaded, waiting for content...")
            await asyncio.sleep(5)
            
            await page.wait_for_selector('div[data-e2e="user-post-item"]', timeout=20000)
        except Exception as e:
            print(f"   Wait error: {e}")
        
        content = await page.content()
        await browser.close()
        
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
            match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?=.*?(\{.*?\});', content, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                user_detail = data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {})
                sec_uid = user_detail.get("userInfo", {}).get("user", {}).get("secUid")
                if sec_uid:
                    return sec_uid
        
        raise Exception("Could not extract secUid from page")

def fetch_videos_batch(sec_uid: str, cursor: int = 0, count: int = 35) -> dict:
    """Fetch a batch of videos using the public API endpoint."""
    url = "https://www.tiktok.com/api/post/item_list/"
    params = {
        "aid": "1988",
        "count": str(count),
        "cursor": str(cursor),
        "device_platform": "web_pc",
        "secUid": sec_uid,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        "Referer": "https://www.tiktok.com/",
    }
    
    response = requests.get(url, params=params, headers=headers, timeout=30)
    return response.json()

def extract_post_data(video: dict) -> dict:
    """Extract relevant data from a video item."""
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

async def extract_video_comments(video_id: str, max_comments: int = None) -> list:
    """
    Extract comments for a TikTok video using the public API.

    Args:
        video_id: TikTok video ID (aweme_id)
        max_comments: Maximum number of comments to extract (None for all)

    Returns:
        List of comment dictionaries with keys matching the expected format
    """
    import aiohttp

    comments = []
    cursor = 0
    has_more = True

    while has_more and (max_comments is None or len(comments) < max_comments):
        try:
            # Calculate how many comments to fetch in this batch
            batch_size = 20  # TikTok API standard batch size
            if max_comments is not None:
                remaining = max_comments - len(comments)
                if remaining <= 0:
                    break
                batch_size = min(batch_size, remaining)

            # Make API request
            url = "https://www.tiktok.com/api/comment/list/"
            params = {
                "aweme_id": video_id,
                "count": str(batch_size),
                "cursor": str(cursor),
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "Referer": "https://www.tiktok.com/",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status != 200:
                        print(f"   Failed to fetch comments for video {video_id}: HTTP {response.status}")
                        break

                    data = await response.json()

            # Extract comments from response
            batch_comments = data.get("comments", [])
            has_more = data.get("has_more", False)
            cursor = data.get("cursor", 0)

            # Process each comment
            for comment in batch_comments:
                try:
                    # Extract comment data
                    comment_id = comment.get("cid")
                    text = comment.get("text", "")
                    create_time = comment.get("create_time")
                    like_count = comment.get("digg_count", 0)

                    # Extract author information
                    user_info = comment.get("user", {})
                    author_name = user_info.get("nickname", "") or user_info.get("unique_id", "")

                    # Convert timestamp
                    if create_time:
                        try:
                            created_time = datetime.fromtimestamp(int(create_time))
                        except (ValueError, TypeError):
                            created_time = None
                    else:
                        created_time = None

                    # Apply NLP analysis
                    analyzer = SentimentAnalyzer()
                    sentiment_label, sentiment_score = analyzer.analyze(text)
                    topic = get_main_topic(text)
                    zona = detect_zona(text)

                    # Build comment dictionary
                    comment_data = {
                        "comment_id": str(comment_id),
                        "video_id": str(video_id),
                        "message": text[:5000],  # Limit to match DB column size
                        "author_name": author_name[:100],  # Limit author name length
                        "created_time": created_time.isoformat() if created_time else None,
                        "like_count": like_count,
                        "sentiment": sentiment_label,
                        "sentiment_score": sentiment_score,
                        "topic_category": topic,
                        "zona": zona,
                    }

                    comments.append(comment_data)

                except Exception as e:
                    print(f"   Error processing comment for video {video_id}: {e}")
                    continue

            # Add delay to avoid rate limiting
            await asyncio.sleep(random.uniform(0.5, 1.5))

        except Exception as e:
            print(f"   Error fetching comments for video {video_id}: {e}")
            break

    return comments


async def scrape_tiktok(username: str, max_videos: int = None):
    """Main scraping function."""
    print(f"\n=== TikTok Scraper - @{username} ===\n")
    
    print("1. Obteniendo secUid...")
    try:
        sec_uid = await get_secuid_with_playwright(username)
        print(f"   ✓ secUid: {sec_uid[:30]}...")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print(f"\n2. Obteniendo videos...")
    all_posts = []
    cursor = 0
    has_more = True
    batch_num = 0
    
    while has_more:
        batch_num += 1
        
        try:
            data = fetch_videos_batch(sec_uid, cursor=cursor)
        except Exception as e:
            print(f"   Error en batch {batch_num}: {e}")
            break
        
        items = data.get("items", [])
        has_more = bool(data.get("has_more"))
        cursor = data.get("cursor", 0)
        
        for item in items:
            post = extract_post_data(item)

            # Extract and save comments for videos with comments
            if post.get("comments", 0) > 0:
                video_id = post.get("video_id")
                # Extract comments (limit to prevent excessive API calls)
                comments = await extract_video_comments(video_id, max_comments=100)  # Limit to 100 comments per video

                # In a real application, we would save these comments to a database
                # For this demo script, we'll just display the count
                if comments:
                    print(f"   -> Found {len(comments)} comments for video {video_id}")

            all_posts.append(post)
        
        print(f"   Batch {batch_num}: {len(items)} videos (total: {len(all_posts)})")
        
        if max_videos and len(all_posts) >= max_videos:
            all_posts = all_posts[:max_videos]
            break
        
        if has_more:
            time.sleep(1)
    
    print(f"\n3. Total videos recolectados: {len(all_posts)}")
    
    print(f"\n4. Guardando datos...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"tiktok_{username}_{timestamp}.json"
    
    output = {
        "username": username,
        "scraped_at": datetime.now().isoformat(),
        "total_posts": len(all_posts),
        "posts": all_posts
    }
    
    output_file.write_text(json.dumps(output, indent=2, default=str))
    print(f"   ✓ Guardado: {output_file}")
    
    if all_posts:
        print(f"\n5. Preview (primer video):")
        p = all_posts[0]
        print(f"   ID: {p['video_id']}")
        print(f"   Desc: {p['description'][:80]}...")
        print(f"   Views: {p['views']:,}")
        print(f"   Likes: {p['likes']:,}")
        print(f"   Comments: {p['comments']:,}")
    
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok Scraper")
    parser.add_argument("--user", default=DEFAULT_USER, help="TikTok username")
    parser.add_argument("--limit", type=int, default=None, help="Max videos to scrape")
    args = parser.parse_args()
    
    asyncio.run(scrape_tiktok(args.user, args.limit))