"""
TikTok Scraper V2 — Requests directos a API interna, sin browser.
Tres fases: Videos → Comentarios → Hilos de respuestas.

Uso:
    scraper = TikTokScraperV2(db)
    scraper.run_phase1_videos("alcaldiasa")
    scraper.run_phase2_comments("alcaldiasa")
    scraper.run_phase3_replies("alcaldiasa")
"""

import json
import logging
import random
import re
import time
from datetime import datetime
from typing import Optional, List, Dict, Tuple

import requests

from .models import TTVideoData, TTCommentData
from .db_local import LocalDB

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

TT_BASE        = "https://www.tiktok.com"
TT_API_USER    = "https://www.tiktok.com/api/user/detail/"
TT_API_VIDEOS  = "https://www.tiktok.com/api/post/item_list/"
TT_API_COMMENTS = "https://www.tiktok.com/api/comment/list/"
TT_API_REPLIES  = "https://www.tiktok.com/api/comment/list/reply/"

# Delays seguros (segundos) — respeta rate limits de TikTok
DELAY_MIN = 2.5
DELAY_MAX = 5.0
DELAY_BURST_EVERY = 80      # cada N requests, pausa larga
DELAY_BURST_MIN   = 30.0    # pausa larga mínima
DELAY_BURST_MAX   = 60.0    # pausa larga máxima

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


# ─────────────────────────────────────────────
# SCRAPER PRINCIPAL
# ─────────────────────────────────────────────

class TikTokScraperV2:

    def __init__(self, db: LocalDB):
        self.db = db
        self.session = self._build_session()
        self.request_count = 0
        self._ms_token: str = ""

    # ── SESIÓN HTTP ───────────────────────────

    def _build_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-SV,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.tiktok.com/",
            "Origin": "https://www.tiktok.com",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive",
        })
        return s

    def _rotate_user_agent(self):
        self.session.headers["User-Agent"] = random.choice(USER_AGENTS)

    def _delay(self):
        """Delay aleatorio entre requests. Pausa larga cada N requests."""
        self.request_count += 1

        if self.request_count % DELAY_BURST_EVERY == 0:
            pause = random.uniform(DELAY_BURST_MIN, DELAY_BURST_MAX)
            logger.info(f"[Pausa burst] {self.request_count} requests → esperando {pause:.1f}s")
            time.sleep(pause)
            self._rotate_user_agent()
        else:
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    def _get(self, url: str, params: dict, retries: int = 3) -> Optional[dict]:
        """GET con reintentos y manejo de rate limiting."""
        for attempt in range(retries):
            try:
                if self._ms_token:
                    params["msToken"] = self._ms_token

                resp = self.session.get(url, params=params, timeout=15)

                if resp.status_code == 429:
                    wait = 120 + random.uniform(0, 60)
                    logger.warning(f"Rate limit 429 → esperando {wait:.0f}s")
                    time.sleep(wait)
                    continue

                if resp.status_code != 200:
                    logger.warning(f"HTTP {resp.status_code} en {url}")
                    time.sleep(10 * (attempt + 1))
                    continue

                return resp.json()

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout en {url} (intento {attempt+1})")
                time.sleep(5)
            except requests.exceptions.ConnectionError:
                logger.warning(f"ConnectionError (intento {attempt+1})")
                time.sleep(15)
            except Exception as e:
                logger.error(f"Error inesperado: {e}")
                time.sleep(5)

        return None

    # ── BOOTSTRAP: obtener secUid y msToken ───

    def bootstrap_user(self, username: str) -> Optional[str]:
        """
        Carga la página del perfil para:
        1. Obtener el msToken de las cookies.
        2. Extraer el secUid desde el HTML embebido.
        Retorna el secUid o None si falla.
        """
        url = f"{TT_BASE}/@{username}"
        logger.info(f"Bootstrap: cargando perfil {url}")

        try:
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()

            # Extraer msToken de cookies
            for cookie in self.session.cookies:
                if cookie.name == "msToken":
                    self._ms_token = cookie.value
                    logger.info("msToken obtenido de cookies")
                    break

            # Extraer secUid del HTML
            sec_uid = self._extract_sec_uid(resp.text, username)
            if sec_uid:
                logger.info(f"secUid encontrado: {sec_uid[:20]}...")
                return sec_uid

            # Fallback: usar API de user detail
            return self._get_sec_uid_api(username)

        except Exception as e:
            logger.error(f"Bootstrap falló para {username}: {e}")
            return None

    def _extract_sec_uid(self, html: str, username: str) -> Optional[str]:
        """Extrae secUid del JSON embebido en la página."""
        patterns = [
            r'"secUid"\s*:\s*"([^"]{50,})"',
            r'"SEC_UID"\s*:\s*"([^"]{50,})"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)

        # Intentar desde SIGI_STATE
        sigi_match = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_VIEW__"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        if sigi_match:
            try:
                data = json.loads(sigi_match.group(1))
                # Navegar la estructura
                user_info = (
                    data.get("__DEFAULT_SCOPE__", {})
                       .get("webapp.user-detail", {})
                       .get("userInfo", {})
                       .get("user", {})
                )
                if user_info.get("secUid"):
                    return user_info["secUid"]
            except Exception:
                pass

        return None

    def _get_sec_uid_api(self, username: str) -> Optional[str]:
        """Obtiene secUid via API de user detail."""
        self._delay()
        data = self._get(TT_API_USER, {
            "uniqueId": username,
            "aid": "1988",
            "app_name": "tiktok_web",
        })
        if data:
            try:
                return data["userInfo"]["user"]["secUid"]
            except (KeyError, TypeError):
                pass
        return None

    # ── FASE 1: VIDEOS ────────────────────────

    def run_phase1_videos(self, username: str) -> int:
        """
        Scrapea todos los videos del perfil con paginación.
        Retorna el total de videos guardados.
        """
        logger.info(f"═══ FASE 1: Videos de @{username} ═══")

        # Verificar checkpoint
        ckpt = self.db.get_checkpoint(username, "videos")
        if ckpt and ckpt["completed"]:
            logger.info(f"Fase 1 ya completada para @{username} ({ckpt['items_done']} videos)")
            return ckpt["items_done"]

        cursor = ckpt["cursor"] if ckpt else "0"
        items_done = ckpt["items_done"] if ckpt else 0
        logger.info(f"Reanudando desde cursor={cursor}, {items_done} videos ya guardados")

        # Bootstrap
        sec_uid = self.bootstrap_user(username)
        if not sec_uid:
            logger.error(f"No se pudo obtener secUid para @{username}")
            return items_done

        # Paginación
        has_more = True
        consecutive_empty = 0

        while has_more:
            self._delay()

            data = self._get(TT_API_VIDEOS, {
                "secUid": sec_uid,
                "count": "30",
                "cursor": cursor,
                "aid": "1988",
                "app_name": "tiktok_web",
                "device_platform": "web_pc",
            })

            if not data:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    logger.warning("3 respuestas vacías consecutivas — deteniendo fase 1")
                    break
                time.sleep(30)
                continue

            consecutive_empty = 0
            videos = data.get("itemList", [])

            if not videos:
                logger.info("No hay más videos — fin de paginación")
                break

            saved_batch = 0
            for item in videos:
                video_data = self._parse_video(item, username)
                if video_data and not self.db.video_exists(video_data["video_id"]):
                    if self.db.upsert_video(video_data):
                        saved_batch += 1

            items_done += saved_batch
            cursor = str(data.get("cursor", "0"))
            has_more = data.get("hasMore", False)

            logger.info(f"  Lote: +{saved_batch} videos | Total: {items_done} | cursor: {cursor}")

            # Guardar checkpoint
            self.db.save_checkpoint(
                username=username,
                phase="videos",
                cursor=cursor,
                items_done=items_done,
                completed=not has_more
            )

        logger.info(f"═══ Fase 1 completada: {items_done} videos de @{username} ═══")
        return items_done

    def _parse_video(self, item: dict, username: str) -> Optional[Dict]:
        """Convierte un item de la API al formato de la DB."""
        try:
            video_id = str(item.get("id", ""))
            if not video_id:
                return None

            stats = item.get("stats", {})
            create_ts = item.get("createTime", 0)

            # Extraer hashtags de la descripción
            desc = item.get("desc", "")
            hashtags = [
                challenge.get("title", "")
                for challenge in item.get("challenges", [])
                if challenge.get("title")
            ]
            # También extraer del texto si no vienen en challenges
            if not hashtags:
                hashtags = re.findall(r"#(\w+)", desc)

            # Thumbnail
            video_info = item.get("video", {})
            thumbnail = (
                video_info.get("cover", "")
                or video_info.get("originCover", "")
                or video_info.get("dynamicCover", "")
            )

            return {
                "video_id": video_id,
                "username": username,
                "description": desc,
                "create_time": datetime.fromtimestamp(create_ts) if create_ts else None,
                "likes_count": stats.get("diggCount", 0),
                "comments_count": stats.get("commentCount", 0),
                "shares_count": stats.get("shareCount", 0),
                "views_count": stats.get("playCount", 0),
                "favorites_count": stats.get("collectCount", 0),
                "hashtags": json.dumps(hashtags),
                "thumbnail_url": thumbnail,
                "video_url": f"https://www.tiktok.com/@{username}/video/{video_id}",
            }

        except Exception as e:
            logger.debug(f"Error parseando video: {e}")
            return None

    # ── FASE 2: COMENTARIOS ───────────────────

    def run_phase2_comments(self, username: str) -> int:
        """
        Scrapea todos los comentarios top-level de cada video.
        """
        logger.info(f"═══ FASE 2: Comentarios de @{username} ═══")

        video_ids = self.db.get_videos_without_comments(username)
        total_videos = len(video_ids)
        logger.info(f"Videos pendientes de comentarios: {total_videos}")

        total_comments = 0
        for idx, video_id in enumerate(video_ids, 1):
            logger.info(f"  [{idx}/{total_videos}] Comentarios del video {video_id}")

            count = self._scrape_comments_for_video(video_id)
            total_comments += count

            # Checkpoint cada 10 videos
            if idx % 10 == 0:
                self.db.save_checkpoint(
                    username=username,
                    phase="comments",
                    cursor=str(idx),
                    last_item_id=video_id,
                    items_done=total_comments,
                )
                logger.info(f"  Checkpoint: {idx}/{total_videos} videos, {total_comments} comentarios")

        self.db.save_checkpoint(
            username=username, phase="comments",
            cursor=str(total_videos), items_done=total_comments, completed=True
        )
        logger.info(f"═══ Fase 2 completada: {total_comments} comentarios ═══")
        return total_comments

    def _scrape_comments_for_video(self, video_id: str) -> int:
        """Pagina todos los comentarios top-level de un video."""
        cursor = "0"
        total = 0
        has_more = True
        consecutive_empty = 0

        while has_more:
            self._delay()

            data = self._get(TT_API_COMMENTS, {
                "aweme_id": video_id,
                "count": "50",
                "cursor": cursor,
                "aid": "1988",
                "app_name": "tiktok_web",
            })

            if not data:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                time.sleep(20)
                continue

            consecutive_empty = 0
            comments = data.get("comments", [])

            if not comments:
                break

            batch = []
            for c in comments:
                parsed = self._parse_comment(c, video_id, parent_id=None, is_reply=False)
                if parsed:
                    batch.append(parsed)

            saved = self.db.bulk_insert_comments(batch)
            total += saved

            cursor = str(data.get("cursor", "0"))
            has_more = bool(data.get("has_more", False))

        return total

    def _parse_comment(self, c: dict, video_id: str,
                       parent_id: Optional[str], is_reply: bool) -> Optional[Dict]:
        try:
            comment_id = str(c.get("cid", ""))
            if not comment_id:
                return None

            ts = c.get("create_time", 0)
            author = c.get("user", {})
            text_data = c.get("text", "")

            return {
                "comment_id": comment_id,
                "video_id": video_id,
                "text": text_data,
                "author_name": author.get("nickname", ""),
                "author_id": str(author.get("uid", "")),
                "create_time": datetime.fromtimestamp(ts) if ts else None,
                "likes_count": c.get("digg_count", 0),
                "parent_comment_id": parent_id,
                "is_reply": is_reply,
                "reply_count": c.get("reply_comment_total", 0) if not is_reply else 0,
            }
        except Exception as e:
            logger.debug(f"Error parseando comentario: {e}")
            return None

    # ── FASE 3: HILOS DE RESPUESTAS ───────────

    def run_phase3_replies(self, username: str) -> int:
        """
        Para cada comentario con respuestas, scrapea los hilos completos.
        """
        logger.info(f"═══ FASE 3: Hilos de respuestas de @{username} ═══")

        # Obtener todos los videos del usuario
        with self.db.Session() as session:
            from sqlalchemy import text
            video_ids = session.execute(
                text("SELECT video_id FROM tt_videos WHERE username = :u"),
                {"u": username}
            ).scalars().all()

        total_replies = 0
        for v_idx, video_id in enumerate(video_ids, 1):
            pending = self.db.get_comments_with_replies(video_id)

            if not pending:
                continue

            logger.info(f"  Video {v_idx}: {len(pending)} comentarios con replies pendientes")

            for c in pending:
                count = self._scrape_replies_for_comment(
                    video_id=video_id,
                    comment_id=c["comment_id"]
                )
                total_replies += count

            # Checkpoint cada 20 videos
            if v_idx % 20 == 0:
                self.db.save_checkpoint(
                    username=username,
                    phase="replies",
                    cursor=str(v_idx),
                    items_done=total_replies
                )

        self.db.save_checkpoint(
            username=username, phase="replies",
            cursor="done", items_done=total_replies, completed=True
        )
        logger.info(f"═══ Fase 3 completada: {total_replies} replies ═══")
        return total_replies

    def _scrape_replies_for_comment(self, video_id: str, comment_id: str) -> int:
        """Pagina todos los replies de un comentario raíz."""
        cursor = "0"
        total = 0
        has_more = True
        consecutive_empty = 0

        while has_more:
            self._delay()

            data = self._get(TT_API_REPLIES, {
                "item_id": video_id,
                "comment_id": comment_id,
                "count": "20",
                "cursor": cursor,
                "aid": "1988",
                "app_name": "tiktok_web",
            })

            if not data:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                time.sleep(20)
                continue

            consecutive_empty = 0
            replies = data.get("comments", [])

            if not replies:
                break

            batch = []
            for r in replies:
                parsed = self._parse_comment(r, video_id, parent_id=comment_id, is_reply=True)
                if parsed:
                    batch.append(parsed)

            saved = self.db.bulk_insert_comments(batch)
            total += saved

            cursor = str(data.get("cursor", "0"))
            has_more = bool(data.get("has_more", False))

        return total