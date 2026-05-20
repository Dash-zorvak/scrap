"""
Base de datos PostgreSQL local para scrapeo de TikTok.
Almacena videos, comentarios e hilos de respuestas.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

logger = logging.getLogger(__name__)

Base = declarative_base()


# ─────────────────────────────────────────────
# MODELOS DE BASE DE DATOS
# ─────────────────────────────────────────────

class TTVideo(Base):
    __tablename__ = "tt_videos"

    video_id        = sa.Column(sa.Text, primary_key=True)
    username        = sa.Column(sa.Text, nullable=False, index=True)
    description     = sa.Column(sa.Text, default="")
    create_time     = sa.Column(sa.DateTime, nullable=True, index=True)

    likes_count     = sa.Column(sa.BigInteger, default=0)
    comments_count  = sa.Column(sa.BigInteger, default=0)
    shares_count    = sa.Column(sa.BigInteger, default=0)
    views_count     = sa.Column(sa.BigInteger, default=0)
    favorites_count = sa.Column(sa.BigInteger, default=0)

    hashtags        = sa.Column(sa.Text, default="")   # JSON array guardado como texto
    thumbnail_url   = sa.Column(sa.Text, default="")
    video_url       = sa.Column(sa.Text, default="")

    scraped_at      = sa.Column(sa.DateTime, default=datetime.utcnow)


class TTComment(Base):
    __tablename__ = "tt_comments"

    comment_id         = sa.Column(sa.Text, primary_key=True)
    video_id           = sa.Column(sa.Text, nullable=False, index=True)

    text               = sa.Column(sa.Text, default="")
    author_name        = sa.Column(sa.Text, default="")
    author_id          = sa.Column(sa.Text, default="")
    create_time        = sa.Column(sa.DateTime, nullable=True)
    likes_count        = sa.Column(sa.BigInteger, default=0)

    parent_comment_id  = sa.Column(sa.Text, nullable=True, index=True)
    is_reply           = sa.Column(sa.Boolean, default=False)
    reply_count        = sa.Column(sa.Integer, default=0)

    scraped_at         = sa.Column(sa.DateTime, default=datetime.utcnow)


class ScrapingCheckpoint(Base):
    """Guarda el estado de cada fase para poder reanudar."""
    __tablename__ = "scraping_checkpoints"

    id              = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    username        = sa.Column(sa.Text, nullable=False)
    phase           = sa.Column(sa.Text, nullable=False)   # 'videos' | 'comments' | 'replies'
    cursor          = sa.Column(sa.Text, default="0")      # cursor de paginación
    last_item_id    = sa.Column(sa.Text, default="")       # último video/comment procesado
    items_done      = sa.Column(sa.Integer, default=0)
    completed       = sa.Column(sa.Boolean, default=False)
    updated_at      = sa.Column(sa.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        sa.UniqueConstraint("username", "phase", name="uq_checkpoint"),
    )


# ─────────────────────────────────────────────
# CLASE PRINCIPAL DE BASE DE DATOS
# ─────────────────────────────────────────────

class LocalDB:
    def __init__(self, db_url: str = "postgresql://localhost/tiktok_scraper"):
        self.engine = sa.create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"Base de datos lista: {db_url}")

    def get_session(self):
        return self.Session()

    # ── VIDEOS ────────────────────────────────

    def upsert_video(self, data: Dict[str, Any]) -> bool:
        try:
            with self.Session() as session:
                existing = session.get(TTVideo, data["video_id"])
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    session.add(TTVideo(**data))
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Error guardando video {data.get('video_id')}: {e}")
            return False

    def video_exists(self, video_id: str) -> bool:
        with self.Session() as session:
            return session.get(TTVideo, video_id) is not None

    def get_videos_without_comments(self, username: str) -> List[str]:
        """Retorna video_ids que aún no tienen comentarios scrapeados."""
        with self.Session() as session:
            scraped = session.execute(
                text("SELECT DISTINCT video_id FROM tt_comments")
            ).scalars().all()
            scraped_set = set(scraped)

            all_ids = session.execute(
                text("SELECT video_id FROM tt_videos WHERE username = :u"),
                {"u": username}
            ).scalars().all()

            return [vid for vid in all_ids if vid not in scraped_set]

    def get_comments_with_replies(self, video_id: str) -> List[Dict]:
        """Retorna comentarios raíz que tienen replies sin scrapear."""
        with self.Session() as session:
            rows = session.execute(
                text("""
                    SELECT comment_id, reply_count
                    FROM tt_comments
                    WHERE video_id = :vid
                      AND is_reply = false
                      AND reply_count > 0
                      AND comment_id NOT IN (
                          SELECT DISTINCT parent_comment_id
                          FROM tt_comments
                          WHERE is_reply = true AND parent_comment_id IS NOT NULL
                      )
                """),
                {"vid": video_id}
            ).fetchall()
            return [{"comment_id": r[0], "reply_count": r[1]} for r in rows]

    # ── COMENTARIOS ───────────────────────────

    def upsert_comment(self, data: Dict[str, Any]) -> bool:
        try:
            with self.Session() as session:
                existing = session.get(TTComment, data["comment_id"])
                if existing:
                    for k, v in data.items():
                        setattr(existing, k, v)
                else:
                    session.add(TTComment(**data))
                session.commit()
            return True
        except Exception as e:
            logger.error(f"Error guardando comentario {data.get('comment_id')}: {e}")
            return False

    def bulk_insert_comments(self, comments: List[Dict]) -> int:
        """Inserta múltiples comentarios ignorando duplicados."""
        if not comments:
            return 0
        saved = 0
        with self.Session() as session:
            for data in comments:
                try:
                    existing = session.get(TTComment, data["comment_id"])
                    if not existing:
                        session.add(TTComment(**data))
                        saved += 1
                except Exception as e:
                    logger.debug(f"Comentario duplicado o error: {e}")
            session.commit()
        return saved

    # ── CHECKPOINTS ───────────────────────────

    def get_checkpoint(self, username: str, phase: str) -> Optional[Dict]:
        with self.Session() as session:
            row = session.execute(
                text("SELECT cursor, last_item_id, items_done, completed FROM scraping_checkpoints WHERE username=:u AND phase=:p"),
                {"u": username, "p": phase}
            ).fetchone()
            if row:
                return {
                    "cursor": row[0],
                    "last_item_id": row[1],
                    "items_done": row[2],
                    "completed": row[3]
                }
            return None

    def save_checkpoint(self, username: str, phase: str, cursor: str,
                        last_item_id: str = "", items_done: int = 0,
                        completed: bool = False):
        with self.Session() as session:
            session.execute(
                text("""
                    INSERT INTO scraping_checkpoints (username, phase, cursor, last_item_id, items_done, completed, updated_at)
                    VALUES (:u, :p, :c, :l, :i, :done, NOW())
                    ON CONFLICT (username, phase) DO UPDATE
                    SET cursor=:c, last_item_id=:l, items_done=:i, completed=:done, updated_at=NOW()
                """),
                {"u": username, "p": phase, "c": cursor, "l": last_item_id,
                 "i": items_done, "done": completed}
            )
            session.commit()

    # ── ESTADÍSTICAS ──────────────────────────

    def get_stats(self) -> Dict:
        with self.Session() as session:
            videos = session.execute(text("SELECT COUNT(*) FROM tt_videos")).scalar()
            comments = session.execute(text("SELECT COUNT(*) FROM tt_comments WHERE is_reply=false")).scalar()
            replies = session.execute(text("SELECT COUNT(*) FROM tt_comments WHERE is_reply=true")).scalar()
            by_user = session.execute(
                text("SELECT username, COUNT(*) FROM tt_videos GROUP BY username")
            ).fetchall()
        return {
            "total_videos": videos,
            "total_comments": comments,
            "total_replies": replies,
            "by_account": {r[0]: r[1] for r in by_user}
        }