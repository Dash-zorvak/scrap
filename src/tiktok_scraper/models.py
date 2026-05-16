from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TTPostData:
    video_id: str
    username: str
    description: str = ""
    create_time: Optional[datetime] = None
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    views_count: int = 0
    video_url: str = ""
    source: str = "playwright"


@dataclass
class TTCommentData:
    comment_id: str
    video_id: str
    message: str = ""
    author_name: str = ""
    create_time: Optional[datetime] = None
    likes_count: int = 0
