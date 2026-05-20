import os
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class FBPost(Base):
    __tablename__ = "fb_posts"

    id = sa.Column(sa.Text, primary_key=True)
    page_id = sa.Column(sa.Text, nullable=False)
    message = sa.Column(sa.Text, default="")
    created_time = sa.Column(sa.DateTime, nullable=True)
    likes_count = sa.Column(sa.Integer, default=0)
    loves_count = sa.Column(sa.Integer, default=0)
    hahas_count = sa.Column(sa.Integer, default=0)
    wows_count = sa.Column(sa.Integer, default=0)
    sads_count = sa.Column(sa.Integer, default=0)
    angrys_count = sa.Column(sa.Integer, default=0)
    comments_count = sa.Column(sa.Integer, default=0)
    shares_count = sa.Column(sa.Integer, default=0)
    post_url = sa.Column(sa.Text, default="")
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())
    source = sa.Column(sa.Text, default="graph_api")


class FBComment(Base):
    __tablename__ = "fb_comments"

    id = sa.Column(sa.Text, primary_key=True)
    post_id = sa.Column(sa.Text, nullable=False, index=True)
    message = sa.Column(sa.Text, default="")
    author_name = sa.Column(sa.Text, default="")
    created_time = sa.Column(sa.DateTime, nullable=True)
    like_count = sa.Column(sa.Integer, default=0)
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())


class TTPost(Base):
    __tablename__ = "tt_posts"

    id = sa.Column(sa.Text, primary_key=True)
    username = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text, default="")
    create_time = sa.Column(sa.DateTime, nullable=True)
    likes_count = sa.Column(sa.Integer, default=0)
    comments_count = sa.Column(sa.Integer, default=0)
    shares_count = sa.Column(sa.Integer, default=0)
    views_count = sa.Column(sa.Integer, default=0)
    favorites_count = sa.Column(sa.Integer, default=0)
    video_url = sa.Column(sa.Text, default="")
    hashtags = sa.Column(sa.Text, default="")
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())


class TTComment(Base):
    __tablename__ = "tt_comments"

    id = sa.Column(sa.Text, primary_key=True)
    video_id = sa.Column(sa.Text, nullable=False, index=True)
    message = sa.Column(sa.Text, default="")
    author_name = sa.Column(sa.Text, default="")
    author_unique_id = sa.Column(sa.Text, default="")
    author_avatar = sa.Column(sa.Text, default="")
    create_time = sa.Column(sa.DateTime, nullable=True)
    likes_count = sa.Column(sa.Integer, default=0)
    reply_count = sa.Column(sa.Integer, default=0)
    sentiment = sa.Column(sa.Text, default="")
    sentiment_score = sa.Column(sa.Float, default=0.0)
    scraped_at = sa.Column(sa.DateTime, server_default=sa.func.now())


class Database:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.engine = sa.create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()
