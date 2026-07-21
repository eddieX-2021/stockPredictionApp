from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RedditPost:
    post_id: str
    ticker: str
    subreddit: str
    title: str
    selftext: str
    author: str
    created_utc: int
    score: int
    num_comments: int
    permalink: str
    url: str

@dataclass
class RedditComment:
    comment_id: str
    post_id: str
    ticker: str
    body: str
    author: str
    created_utc: int
    score: int
    permalink: str
