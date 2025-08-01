import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.normpath(os.path.join(HERE, '..', 'src'))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from fetch_reddit import fetch_reddit
from predictor     import predict_sentiments

def main():
    company = input("🔍 Enter a company or keyword: ").strip()
    if not company:
        print("Please enter something!")
        return
    search_term = f"{company} stock"
    print(f"\nFetching Reddit posts for '{company}'…")
    posts = fetch_reddit(search_term , limit=5)
    if not posts:
        print("⚠️  No Reddit posts found.")
        return

    print("\n🗒️  Posts:")
    for i, p in enumerate(posts, 1):
        print(f"{i}. {p}")

    results = predict_sentiments(posts)
    print("\n🤖 Sentiment predictions:")
    for p, s in zip(posts, results):
        print(f"• {s.upper():>8}  ← {p}")

if __name__ == '__main__':
    main()