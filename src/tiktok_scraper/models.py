from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class TTVideoData:
    """Datos completos de un video de TikTok."""
    video_id: str
    username: str
    description: str = ""
    create_time: Optional[datetime] = None

    # Métricas de engagement
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0
    favorites_count: int = 0         # ← nuevo

    # Metadata
    hashtags: List[str] = field(default_factory=list)   # ← nuevo
    thumbnail_url: str = ""                              # ← nuevo
    video_url: str = ""

    source: str = "api_v2"


@dataclass
class TTCommentData:
    """Comentario o respuesta de un video de TikTok."""
    comment_id: str
    video_id: str

    text: str = ""
    author_name: str = ""
    author_id: str = ""
    create_time: Optional[datetime] = None
    likes_count: int = 0

    # Soporte para hilos
    parent_comment_id: Optional[str] = None   # None = comentario raíz
    is_reply: bool = False
    reply_count: int = 0                       # cuántas respuestas tiene (solo en raíz)