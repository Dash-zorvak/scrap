from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class FBPostData:
    post_id: str
    page_id: str
    message: str = ""
    created_time: Optional[datetime] = None
    likes_count: int = 0
    loves_count: int = 0
    hahas_count: int = 0
    wows_count: int = 0
    sads_count: int = 0
    angrys_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    post_url: str = ""
    source: str = "graph_api"


@dataclass
class FBCommentData:
    comment_id: str
    post_id: str
    message: str = ""
    author_name: str = ""
    created_time: Optional[datetime] = None
    like_count: int = 0


@dataclass
class FBPageInfo:
    page_id: str
    page_name: str
    page_url: str = ""
