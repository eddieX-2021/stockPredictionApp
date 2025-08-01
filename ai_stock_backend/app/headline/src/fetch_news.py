import os
from dotenv import load_dotenv
from newsapi import NewsApiClient

load_dotenv()  # loads NEWSAPI_KEY from .env

API_KEY = os.getenv('NEWS_API_KEY')
if not API_KEY:
    raise RuntimeError("Set NEWSAPI_KEY in your .env file")

newsapi = NewsApiClient(api_key=API_KEY)

def get_top_headlines(query: str, page_size: int = 5):
    """
    Fetch top `page_size` English headlines matching `query`.
    """
    resp = newsapi.get_everything(
        q=query,
        language='en',
        sort_by='publishedAt',
        page_size=page_size
    )
    return [art['title'] for art in resp.get('articles', [])]