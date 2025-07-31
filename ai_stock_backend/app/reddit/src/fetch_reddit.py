import os
from typing import List
from dotenv import load_dotenv
import praw

# point to your project root .env
dotenv_path = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
)
load_dotenv(dotenv_path)

CLIENT_ID     = os.getenv('REDDIT_CLIENT_ID')
CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
USER_AGENT    = os.getenv('REDDIT_USER_AGENT')

reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    user_agent=USER_AGENT
)

def fetch_reddit(ticker: str, limit: int = 5) -> List[str]:
    """
    Search Reddit for the given ticker symbol and return post titles.
    """
    try:
        results = reddit.subreddit('all').search(
            ticker,
            sort='new',
            limit=limit,
            syntax='lucene'
        )
        return [post.title for post in results]
    except Exception:
        return []
