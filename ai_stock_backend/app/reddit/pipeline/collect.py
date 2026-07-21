from __future__ import annotations
import json
from datetime import datetime
from typing import List

from ..reddit_client import RedditClient
from ..models.schemas import RedditPost, RedditComment
from ..storage.sqlite_store import SQLiteRedditStore
from ..storage.paths import RAW_DIR, ensure_dirs

def _tag() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def collect_for_ticker(
    ticker: str,
    subreddits: str = "TheRaceTo10Million+StockMarket+wallstreetbets+wallstreetstockpicks",
    post_limit: int = 25,
    top_comments_per_post: int = 30,
    time_filter: str = "week",
) -> dict:
    ensure_dirs()
    rc = RedditClient()
    store = SQLiteRedditStore()

    ticker = ticker.upper()
    query = f'("{ticker}" OR "${ticker}")'

    raw_path = f"{RAW_DIR}/{ticker}_{_tag()}.jsonl"
    posts_saved = 0
    comments_saved = 0

    with open(raw_path, "w", encoding="utf-8") as f:
        for s in rc.search_posts(query=query, subreddits=subreddits, limit=post_limit, time_filter=time_filter):
            posts_saved += 1
            s.comments.replace_more(limit=0)

            post = RedditPost(
                post_id=s.id,
                ticker=ticker,
                subreddit=str(s.subreddit),
                title=s.title or "",
                selftext=s.selftext or "",
                author=str(s.author) if s.author else "[deleted]",
                created_utc=int(s.created_utc),
                score=int(s.score or 0),
                num_comments=int(s.num_comments or 0),
                permalink="https://www.reddit.com" + (s.permalink or ""),
                url=s.url or "",
            )
            store.upsert_post(post)

            all_comments = list(s.comments.list())
            all_comments.sort(key=lambda c: getattr(c, "score", 0), reverse=True)
            top = all_comments[:top_comments_per_post]

            comments: List[RedditComment] = []
            for c in top:
                body = getattr(c, "body", "") or ""
                if not body.strip():
                    continue
                cid = getattr(c, "id", "") or ""
                if not cid:
                    continue
                comments.append(RedditComment(
                    comment_id=cid,
                    post_id=s.id,
                    ticker=ticker,
                    body=body,
                    author=str(getattr(c, "author", None)) if getattr(c, "author", None) else "[deleted]",
                    created_utc=int(getattr(c, "created_utc", 0) or 0),
                    score=int(getattr(c, "score", 0) or 0),
                    permalink="https://www.reddit.com" + (getattr(c, "permalink", "") or ""),
                ))

            if comments:
                store.upsert_comments(comments)
                comments_saved += len(comments)

            f.write(json.dumps({
                "ticker": ticker,
                "post": post.__dict__,
                "top_comments": [c.__dict__ for c in comments],
            }, ensure_ascii=False) + "\n")

    return {
        "ticker": ticker,
        "posts_saved": posts_saved,
        "comments_saved": comments_saved,
        "raw_snapshot": raw_path,
        "subreddits": subreddits,
        "time_filter": time_filter,
    }
