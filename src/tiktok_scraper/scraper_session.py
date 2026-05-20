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

import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.analyzer.sentiment import SentimentAnalyzer
from src.analyzer.topic_detection import get_main_topic, detect_zona

OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "tiktok"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

USERNAME = "alcaldiasa"


async def check_login(page):
    try:
        await page.wait_for_selector('div[data-e2e="top-nav-avatar"], a[href*="/@"]', timeout=3000)
        return True
    except:
        return False


async def extract_user_data(page):
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
        else:
            print("   ✗ No pude obtener datos del perfil")
            await browser.close()
            return

        print(f"\n5. Scraping videos...")
        videos = await scroll_and_collect(page, max_videos=50)
        print(f"   ✓ Videos recolectados: {len(videos)}")

        print("\n6. Extrayendo datos de cada video...")
        analyzer = SentimentAnalyzer()
        posts = []

        for i, video in enumerate(videos):
            desc = video.get("desc", "")
            stats = video.get("stats", {})

            sentiment, score = analyzer.analyze(desc)
            topic = get_main_topic(desc)
            zona = detect_zona(desc)

            post_data = {
                "video_id": video.get("id"),
                "description": desc,
                "create_time": datetime.fromtimestamp(int(video.get("createTime", 0))).isoformat(),
                "likes_count": stats.get("diggCount", 0),
                "comments_count": stats.get("commentCount", 0),
                "shares_count": stats.get("shareCount", 0),
                "views_count": stats.get("playCount", 0),
                "favorites_count": stats.get("collectCount", 0),
                "hashtags": re.findall(r'#(\w+)', desc),
                "sentiment": sentiment,
                "sentiment_score": score,
                "topic_category": topic,
                "zona": zona,
            }
            posts.append(post_data)

            if (i + 1) % 10 == 0:
                print(f"   Procesados: {i + 1}/{len(videos)}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"tiktok_alcaldiasa_{timestamp}.json"

        user_final = user_data.get("user", {}) if user_data else {}
        stats_final = user_data.get("stats", {}) if user_data else {}

        # FIX: todas las comillas consistentes
        output = {
            "profile": {
                "username": USERNAME,
                "nickname": user_final.get("nickname"),
                "followers": stats_final.get("followerCount"),   # ← corregido
                "following": stats_final.get("followingCount"),
                "videos": stats_final.get("awemeCount"),
                "total_likes": stats_final.get("totalLikes"),
            },
            "posts": posts,
            "scraped_at": datetime.now().isoformat(),
            "total_posts": len(posts)
        }

        output_file.write_text(json.dumps(output, indent=2, default=str))
        print(f"\n✓ Datos guardados: {output_file}")
        print(f"  Total posts: {len(posts)}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())