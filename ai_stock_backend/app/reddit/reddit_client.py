from __future__ import annotations
from typing import Iterable
import praw
from .config import get_reddit_config

class RedditClient:
    def __init__(self):
        cfg = get_reddit_config()
        self.reddit = praw.Reddit(
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            user_agent=cfg.user_agent,
        )

    def search_posts(
        self,
        query: str,
        subreddits = "TheRaceTo10Million+StockMarket+wallstreetbets+wallstreetstockpicks",
        sort: str = "new",
        limit: int = 25,
        time_filter: str = "week",
    ) -> Iterable[praw.models.Submission]:
        sr = self.reddit.subreddit(subreddits)
        return sr.search(
            query,
            sort=sort,
            limit=limit,
            time_filter=time_filter,
            syntax="lucene",
        )
