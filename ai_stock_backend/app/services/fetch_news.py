import os
from dotenv import load_dotenv
from newsapi import NewsApiClient
import time

load_dotenv()  # loads NEWSAPI_KEY from .env

API_KEY = os.getenv('NEWS_API_KEY')
if not API_KEY:
    raise RuntimeError("Set NEWS_API_KEY in your .env file")

newsapi = NewsApiClient(api_key=API_KEY)

def get_top_headlines(query: str, page_size: int = 5, timeout: int = 10):
    """
    Fetch top `page_size` English headlines matching `query`.
    Returns empty list on error instead of crashing.
    """
    try:
        start_time = time.time()
        
        resp = newsapi.get_everything(
            q=query,
            language='en',
            sort_by='publishedAt',
            page_size=page_size
        )
        
        elapsed = time.time() - start_time
        print(f"News API call for '{query}' took {elapsed:.2f}s")
        
        if not resp or 'articles' not in resp:
            print(f"No articles in response for {query}")
            return []
        
        articles = resp.get('articles', [])
        headlines = [art['title'] for art in articles if art.get('title')]
        
        print(f"Found {len(headlines)} headlines for {query}")
        return headlines
        
    except Exception as e:
        print(f"Error fetching news for {query}: {e}")
        return []  # Return empty list instead of crashing