from __future__ import annotations
import sqlite3
from typing import Iterable, List, Optional, Tuple
from .paths import DB_PATH, ensure_dirs
from ..models.schemas import RedditPost, RedditComment

class SQLiteRedditStore:
    def __init__(self):
        ensure_dirs()
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            ticker TEXT,
            subreddit TEXT,
            title TEXT,
            selftext TEXT,
            author TEXT,
            created_utc INTEGER,
            score INTEGER,
            num_comments INTEGER,
            permalink TEXT,
            url TEXT
        );
        """)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            post_id TEXT,
            ticker TEXT,
            body TEXT,
            author TEXT,
            created_utc INTEGER,
            score INTEGER,
            permalink TEXT,
            FOREIGN KEY(post_id) REFERENCES posts(post_id)
        );
        """)
        self.conn.commit()

    def upsert_post(self, p: RedditPost):
        self.conn.execute("""
        INSERT INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(post_id) DO UPDATE SET
            ticker=excluded.ticker,
            subreddit=excluded.subreddit,
            title=excluded.title,
            selftext=excluded.selftext,
            author=excluded.author,
            created_utc=excluded.created_utc,
            score=excluded.score,
            num_comments=excluded.num_comments,
            permalink=excluded.permalink,
            url=excluded.url
        """, (
            p.post_id, p.ticker, p.subreddit, p.title, p.selftext, p.author,
            p.created_utc, p.score, p.num_comments, p.permalink, p.url
        ))
        self.conn.commit()

    def upsert_comments(self, comments: Iterable[RedditComment]):
        self.conn.executemany("""
        INSERT INTO comments VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(comment_id) DO UPDATE SET
            post_id=excluded.post_id,
            ticker=excluded.ticker,
            body=excluded.body,
            author=excluded.author,
            created_utc=excluded.created_utc,
            score=excluded.score,
            permalink=excluded.permalink
        """, [
            (c.comment_id, c.post_id, c.ticker, c.body, c.author, c.created_utc, c.score, c.permalink)
            for c in comments
        ])
        self.conn.commit()

    def fetch_comments_for_ticker(self, ticker: str, limit: int = 5000) -> List[Tuple]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT comment_id, post_id, ticker, body, score, created_utc, permalink
            FROM comments
            WHERE ticker = ?
            ORDER BY created_utc DESC
            LIMIT ?
        """, (ticker.upper(), limit))
        return cur.fetchall()
