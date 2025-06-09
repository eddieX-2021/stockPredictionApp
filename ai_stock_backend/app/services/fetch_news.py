from newsapi import NewsApiClient
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

load_dotenv() 

api_key = os.getenv("NEWS_API_KEY")

newsapi = NewsApiClient(api_key=api_key)

def fetch_headlines(stock_symbol: str, from_days_ago=7):
    query = stock_symbol
    from_date = (datetime.now() - timedelta(days=from_days_ago)).strftime('%Y-%m-%d')

    articles = newsapi.get_everything(q=query,
                                      from_param=from_date,
                                      sort_by='relevancy',
                                      language='en',
                                      page_size=100)

    headlines = []
    for article in articles['articles']:
        headlines.append({
            'date': article['publishedAt'],
            'source': article['source']['name'],
            'title': article['title'],
            'description': article['description']
        })

    df = pd.DataFrame(headlines)
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df
