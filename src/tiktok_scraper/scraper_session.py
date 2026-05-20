#!/usr/bin/env python3
"""
TikTok Scraper con sesión activa - Mantiene navegador abierto y hace scrapeo.
Usage: python scraper_session.py
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright
import random
import time

# Add imports for NLP analysis
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona, extract_problematicas

OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "tiktok"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

USERNAME = "alcaldiasa"


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

async def check_login(page):
    """Check if user is logged in by looking for profile button."""
    try:
        await page.wait_for_selector('div[data-e2e="top-nav-avatar"], a[href*="/@"]', timeout=3000)
        return True
    except:
        return False

async def extract_user_data(page):
    """Extract user profile data from page."""
    content = await page.content()
    
    if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in content:
        match = re.search(r'__UNIVERSAL_DATA_FOR_REHYDRATION__.*?=.*?(\{.*?\});', content, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            
            if "webapp.user-detail" in data:
                user = data["webapp.user-detail"]
                return {
                    "user": user.get("user", {}),
                    "stats": user.get("stats", {}),
                    "items": user.get("awemeList", [])
                }
    return None

async def scroll_and_collect(page, max_videos=100):
    """Scroll through profile to load videos."""
    videos = []
    seen_ids = set()
    last_height = 0
    
    print(f"  Collecting videos (max: {max_videos})...")
    
    while len(videos) < max_videos:
        user_data = await extract_user_data(page)
        if user_data and user_data.get("items"):
            for item in user_data["items"]:
                video_id = item.get("id")
                if video_id and video_id not in seen_ids:
                    seen_ids.add(video_id)
                    videos.append(item)
                    
                    if len(videos) % 10 == 0:
                        print(f"    Videos loaded: {len(videos)}")
        
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(1)
        
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    return videos

async def main():
    print("=== TikTok Scraper con Sesión Activa ===\n")
    print("1. Browser se abrirá - hacé login si no estás logueado")
    print("2. El script detectará cuando estés logueado")
    print("3. Automáticamente empezará a scrapear\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        print(f"2. Abriendo TikTok...")
        await page.goto(f"https://www.tiktok.com/@{USERNAME}")
        await page.wait_for_load_state("networkidle")
        
        print("3. Verificando si estás logueado...")
        
        logged_in = await check_login(page)
        
        if not logged_in:
            print("   ⚠️ No detecté sesión activa.")
            print("   Por favor hacé login en el navegador.")
            print("   El script esperará 120 segundos...")
            await asyncio.sleep(120)
        
        print("   ✓ Sesión detectada!")
        
        print("\n4. Obteniendo datos del perfil...")
        user_data = await extract_user_data(page)
        
        if user_data:
            user = user_data.get("user", {})
            stats = user_data.get("stats", {})
            
            print(f"   Usuario: {user.get('nickname')}")
            print(f"   @: {user.get('uniqueId')}")
            print(f"   Seguidores: {stats.get('followerCount')}")
            print(f"   Videos: {stats.get('awemeCount')}")
            print(f"   Likes: {stats.get('totalLikes')}")
        else:
            print("   ✗ No pude obtener datos del perfil")
            await browser.close()
            return
        
        print(f"\n5. Scraping videos...")
        videos = await scroll_and_collect(page, max_videos=50)
        
        print(f"   ✓ Videos recolectados: {len(videos)}")
        
        print("\n6. Extrayendo datos de cada video...")
        
        posts = []
        for i, video in enumerate(videos):
            desc = video.get("desc", "")
            stats = video.get("stats", {})

            post_data = {
                "video_id": video.get("id"),
                "description": desc,
                "create_time": datetime.fromtimestamp(int(video.get("createTime", 0))),
                "likes": stats.get("diggCount"),
                "comments": stats.get("commentCount"),
                "shares": stats.get("shareCount"),
                "saves": stats.get("collectCount"),
                "views": stats.get("playCount"),
                "hashtags": re.findall(r'#(\w+)', desc),
                "mentions": re.findall(r'@(\w+)', desc),
            }
            posts.append(post_data)

            # Extract and save comments for videos with comments
            if stats.get("commentCount", 0) > 0:
                video_id = video.get("id")
                # Extract comments (limit to prevent excessive API calls)
                comments = await extract_video_comments(video_id, max_comments=100)  # Limit to 100 comments per video

                # In a real application, we would save these comments to a database
                # For this demo script, we'll just display the count
                if comments:
                    print(f"   -> Found {len(comments)} comments for video {video_id}")

            if (i + 1) % 10 == 0:
                print(f"   Procesados: {i + 1}/{len(videos)}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"tiktok_alcaldiasa_{timestamp}.json"
        
        output = {
            "profile": {
                "username": USERNAME,
                "nickname": user.get("nickname"),
                "followers": stats.get("followerCount'),
                "following": stats.get("followingCount"),
                "videos": stats.get("awemeCount"),
                "total_likes": stats.get("totalLikes"),
            },
            "posts": posts,
            "scraped_at": datetime.now().isoformat(),
            "total_posts": len(posts)
        }
        
        output_file.write_text(json.dumps(output, indent=2, default=str))
        print(f"\n✓ Datos guardados: {output_file}")
        print(f"  Total posts: {len(posts)}")
        
        print("\n7. ¿Continuar con más videos? (cerrar browser para terminar)")
        print("   Presiona Ctrl+C para terminar...")
        
        try:
            await asyncio.sleep(3600)
        except:
            pass
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())