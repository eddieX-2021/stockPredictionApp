"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

type NewsItem = { headline: string; sentiment: string };
type RedditItem = { post: string; sentiment: string };
// avoid `any` by using a more general unknown-shaped object
type Financials = Record<string, unknown>;

export default function StockPage() {
  const params = useParams();
  const raw = params.stock;           // ← changed `let` to `const`
  const ticker = Array.isArray(raw) ? raw[0] ?? "" : raw ?? "";
  const T = ticker.toUpperCase();

  const [predictedPrice, setPredictedPrice] = useState<number | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [reddit, setReddit] = useState<RedditItem[]>([]);
  const [financials, setFinancials] = useState<Financials | null>(null);
  const [direction, setDirection] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!T) return;
    const API =
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    Promise.all([
      fetch(`${API}/predict?stock=${T}`).then((r) =>
        r.ok ? r.json() : Promise.reject("Price API failed")
      ),
      fetch(`${API}/api/news`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: T }),
      }).then((r) => (r.ok ? r.json() : Promise.reject("News API failed"))),
      fetch(`${API}/api/reddit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: T }),
      }).then((r) =>
        r.ok ? r.json() : Promise.reject("Reddit API failed")
      ),
      fetch(`${API}/api/financials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: T }),
      }).then((r) =>
        r.ok ? r.json() : Promise.reject("Financials API failed")
      ),
    ])
      .then(([priceJson, newsJson, redditJson, finJson]) => {
        setPredictedPrice(priceJson.predicted_price ?? null);
        setNews(newsJson.news ?? []);
        setReddit(redditJson.reddit ?? []);
        setFinancials(finJson.financials ?? null);
        setDirection(finJson.direction ?? null);
        setConfidence(finJson.confidence ?? null);
      })
      .catch((err) => setError(String(err)));
  }, [T]);

  if (error) {
    return (
      <p className="text-red-600 p-6">
        Error: {error}
      </p>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-4xl font-bold mb-8 text-center">{T} Dashboard</h1>

      {/* 1. Price Prediction */}
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">Price Prediction</h2>
        {predictedPrice !== null
          ? <p className="text-xl">
              Predicted Price: <strong>${predictedPrice.toFixed(2)}</strong>
            </p>
          : <p className="text-gray-500">Loading price prediction…</p>
        }
      </section>

      {/* 2. News Sentiment */}
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">News Sentiment</h2>
        <ul className="list-disc pl-5">
          {news.length
            ? news.map((n, i) => (
                <li key={i}>
                  <span className="font-medium">{n.sentiment.toUpperCase()}</span>: {n.headline}
                </li>
              ))
            : <p className="text-gray-500">Loading news…</p>
          }
        </ul>
      </section>

      {/* 3. Reddit Sentiment */}
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">Reddit Sentiment</h2>
        <ul className="list-disc pl-5">
          {reddit.length
            ? reddit.map((r, i) => (
                <li key={i}>
                  <span className="font-medium">{r.sentiment.toUpperCase()}</span>: {r.post}
                </li>
              ))
            : <p className="text-gray-500">Loading Reddit posts…</p>
          }
        </ul>
      </section>

      {/* 4. Financials & Direction */}
      <section className="p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">Financials & Prediction</h2>
        {financials
          ? (
            <>
              <pre className="bg-gray-100 p-4 rounded mb-4">
                {JSON.stringify(financials, null, 2)}
              </pre>
              {direction && confidence !== null && (
                <p className="text-lg">
                  Model predicts <strong>{direction}</strong> with{" "}
                  <strong>{(confidence * 100).toFixed(1)}%</strong> confidence.
                </p>
              )}
            </>
          )
          : <p className="text-gray-500">Loading financials…</p>
        }
      </section>
    </div>
  );
}
