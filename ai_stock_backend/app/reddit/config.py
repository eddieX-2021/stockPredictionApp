import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class RedditConfig:
    client_id: str
    client_secret: str
    user_agent: str

def get_reddit_config() -> RedditConfig:
    cid = os.getenv("REDDIT_CLIENT_ID", "").strip()
    sec = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    ua = os.getenv("REDDIT_USER_AGENT", "ai_stock_backend").strip()

    missing = [k for k, v in {
        "REDDIT_CLIENT_ID": cid,
        "REDDIT_CLIENT_SECRET": sec,
    }.items() if not v]

    if missing:
        raise RuntimeError(f"Missing env vars: {missing}. Add them to your .env")

    return RedditConfig(client_id=cid, client_secret=sec, user_agent=ua)
