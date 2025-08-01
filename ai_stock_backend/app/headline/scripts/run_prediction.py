import os
import sys


HERE    = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.normpath(os.path.join(HERE, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


from fetch_news import get_top_headlines
from predictor  import predict_sentiments


def main():
    company = input("🔍 Enter a company or keyword: ").strip()
    if not company:
        print("Please enter something!")
        return

    print(f"\nFetching top headlines for “{company}”…")
    headlines = get_top_headlines(company)
    if not headlines:
        print("⚠️  No articles found.")
        return

    print("\n📰 Headlines:")
    for i, h in enumerate(headlines, 1):
        print(f"{i}. {h}")

    results = predict_sentiments(headlines)
    print("\n🤖 Sentiment predictions:")
    for h, s in zip(headlines, results):
        print(f"• {s.upper():>8}  ← {h}")

if __name__ == '__main__':
    main()