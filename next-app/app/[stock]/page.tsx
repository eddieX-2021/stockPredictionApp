"use client";
export const dynamic = "force-dynamic";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { StatCard } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import { SentimentBar } from "../components/ui/SentimentBar";

type NewsItem = { headline: string; sentiment: string };
type RedditItem = { post: string; sentiment: string };
type Financials = Record<string, any>;

type PredictionData = {
  stock: string;
  current_price: number;
  predicted_price: number;
  direction: string; // "UP" | "DOWN" (assumed)
  confidence: number; // 0..1
  predicted_change_pct: number;
  system_confidence: string;
  model_info: {
    direction_model: string;
    magnitude_model: string;
  };
};

function money(n: number) {
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function pct(n: number) {
  if (!Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function toneFromDirection(dir: string) {
  const d = (dir || "").toUpperCase();
  if (d === "UP") return "good";
  if (d === "DOWN") return "bad";
  return "neutral";
}

function normalizeSentiment(s: string) {
  const x = (s || "").toLowerCase();
  if (x.includes("pos")) return "positive";
  if (x.includes("neg")) return "negative";
  if (x.includes("neu")) return "neutral";
  return "neutral";
}

function pickKeyFinancials(fin: Financials | null) {
  if (!fin) return [];

  // Try common names first, but don’t break if backend changes.
  const candidates: Array<[string, string[]]> = [
    ["Market Cap", ["marketCap", "market_cap", "marketcapitalization"]],
    ["P/E", ["pe", "peRatio", "trailingPE", "p_e"]],
    ["EPS", ["eps", "ttmEPS", "earningsPerShare"]],
    ["Revenue", ["revenue", "totalRevenue"]],
    ["Gross Margin", ["grossMargin", "gross_margin"]],
    ["Operating Margin", ["operatingMargin", "operating_margin"]],
    ["Profit Margin", ["profitMargin", "profit_margin"]],
    ["ROE", ["roe", "returnOnEquity"]],
    ["Debt/Equity", ["debtToEquity", "debt_equity"]],
    ["Free Cash Flow", ["freeCashFlow", "free_cash_flow", "fcf"]],
  ];

  const found: Array<{ label: string; value: any }> = [];

  for (const [label, keys] of candidates) {
    for (const k of keys) {
      if (fin[k] !== undefined && fin[k] !== null) {
        found.push({ label, value: fin[k] });
        break;
      }
    }
  }

  // If we found nothing, fall back to “top numeric fields”
  if (found.length === 0) {
    const numeric = Object.entries(fin)
      .filter(([, v]) => typeof v === "number" && Number.isFinite(v))
      .slice(0, 10)
      .map(([k, v]) => ({ label: k, value: v }));
    return numeric;
  }

  return found;
}

export default function StockPage() {
  const params = useParams();
  const raw = params.stock;
  const ticker = Array.isArray(raw) ? raw[0] ?? "" : raw ?? "";
  const T = ticker.toUpperCase();

  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [reddit, setReddit] = useState<RedditItem[]>([]);
  const [financials, setFinancials] = useState<Financials | null>(null);

  const [direction2, setDirection2] = useState<string | null>(null);
  const [confidence2, setConfidence2] = useState<number | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!T) return;
    const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    setLoading(true);
    setError(null);

    Promise.all([
      fetch(`${API}/predict?stock=${T}`).then((r) =>
        r.ok ? r.json() : Promise.reject("Prediction API failed")
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
      }).then((r) => (r.ok ? r.json() : Promise.reject("Reddit API failed"))),
      fetch(`${API}/api/financials`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: T }),
      }).then((r) => (r.ok ? r.json() : Promise.reject("Financials API failed"))),
    ])
      .then(([predJson, newsJson, redditJson, finJson]) => {
        setPrediction(predJson);
        setNews(newsJson.news ?? []);
        setReddit(redditJson.reddit ?? []);
        setFinancials(finJson.financials ?? null);

        // You had these in your current file; keep them if your backend returns them.
        setDirection2(finJson.direction ?? null);
        setConfidence2(finJson.confidence ?? null);
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [T]);

  const sentimentSummary = useMemo(() => {
    const count = (items: Array<{ sentiment: string }>) => {
      const res = { positive: 0, negative: 0, neutral: 0, total: 0 };
      for (const it of items) {
        const k = normalizeSentiment(it.sentiment) as "positive" | "negative" | "neutral";
        res[k] += 1;
        res.total += 1;
      }
      return res;
    };

    return { news: count(news), reddit: count(reddit) };
  }, [news, reddit]);

  const keyFinancials = useMemo(() => pickKeyFinancials(financials), [financials]);

  if (error) {
    return (
      <div className="min-h-screen bg-bg">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
            ← Back
          </Link>
          <div className="mt-6 rounded-2xl border border-border bg-card p-6">
            <div className="text-lg font-semibold">Something went wrong</div>
            <p className="mt-2 text-sm text-muted-foreground">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const dir = prediction?.direction?.toUpperCase() ?? "—";
  const changePct = prediction?.predicted_change_pct ?? NaN;

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-card/60 backdrop-blur">
        <div className="mx-auto max-w-6xl px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
              ← Back
            </Link>
            <div className="h-6 w-px bg-border" />
            <div>
              <div className="text-sm text-muted-foreground">Dashboard</div>
              <div className="text-xl font-semibold tracking-tight">{T}</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {prediction ? (
              <Badge tone={toneFromDirection(dir) as any}>
                {dir === "UP" ? "Bullish" : dir === "DOWN" ? "Bearish" : "Mixed"}
              </Badge>
            ) : (
              <Badge tone="neutral">{loading ? "Loading…" : "No data"}</Badge>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10 space-y-10">
        {/* Top stats */}
        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Current Price"
            value={prediction ? money(prediction.current_price) : "—"}
            subvalue="Latest available price"
          />
          <StatCard
            title="Predicted Price"
            value={prediction ? money(prediction.predicted_price) : "—"}
            subvalue="Model estimate (next step)"
            badge={
              prediction
                ? { text: dir === "UP" ? "UP" : dir === "DOWN" ? "DOWN" : "—", tone: toneFromDirection(dir) as any }
                : undefined
            }
          />
          <StatCard
            title="Predicted Change"
            value={prediction ? pct(prediction.predicted_change_pct) : "—"}
            subvalue={prediction ? `Direction: ${dir}` : "—"}
            badge={
              prediction
                ? { text: prediction.system_confidence?.toUpperCase?.() ?? "—", tone: "neutral" }
                : undefined
            }
          />
          <StatCard
            title="Confidence"
            value={prediction ? `${(prediction.confidence * 100).toFixed(1)}%` : "—"}
            subvalue={
              prediction
                ? `Models: ${prediction.model_info.direction_model} + ${prediction.model_info.magnitude_model}`
                : "—"
            }
          />
        </section>

        {/* Confidence bar + note */}
        <section className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-lg font-semibold">Model confidence</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Confidence reflects how strongly the model agrees with the signal mix (historical price, sentiment, fundamentals).
              </p>
            </div>
            {prediction ? (
              <Badge tone={toneFromDirection(dir) as any}>
                {dir === "UP" ? "↑ Upward bias" : dir === "DOWN" ? "↓ Downward bias" : "—"}
              </Badge>
            ) : null}
          </div>

          <div className="mt-4 h-3 w-full rounded-full bg-black/5 overflow-hidden">
            <div
              className="h-full bg-black"
              style={{ width: `${prediction ? Math.round(prediction.confidence * 100) : 0}%` }}
            />
          </div>

          <div className="mt-3 text-sm text-muted-foreground">
            {prediction ? (
              <>
                System confidence:{" "}
                <span className="font-medium text-foreground">
                  {prediction.system_confidence?.toUpperCase?.() ?? "—"}
                </span>{" "}
                • Predicted move:{" "}
                <span className="font-medium text-foreground">{pct(changePct)}</span>
              </>
            ) : (
              loading ? "Generating prediction…" : "No prediction yet."
            )}
          </div>
        </section>

        {/* Sentiment overview */}
        <section className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-border bg-card p-6">
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">News sentiment</div>
              <Badge tone="neutral">{sentimentSummary.news.total} items</Badge>
            </div>
            <div className="mt-4 space-y-3">
              <SentimentBar label="Positive" value={sentimentSummary.news.positive} total={sentimentSummary.news.total} />
              <SentimentBar label="Neutral" value={sentimentSummary.news.neutral} total={sentimentSummary.news.total} />
              <SentimentBar label="Negative" value={sentimentSummary.news.negative} total={sentimentSummary.news.total} />
            </div>

            <div className="mt-6">
              <div className="text-sm font-medium">Top headlines</div>
              <ul className="mt-2 space-y-2">
                {(news ?? []).slice(0, 6).map((n, i) => {
                  const s = normalizeSentiment(n.sentiment);
                  return (
                    <li key={i} className="rounded-xl border border-border bg-white p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="text-sm leading-snug">{n.headline}</div>
                        <Badge
                          tone={s === "positive" ? "good" : s === "negative" ? "bad" : "neutral"}
                        >
                          {s}
                        </Badge>
                      </div>
                    </li>
                  );
                })}
                {!news?.length && (
                  <li className="text-sm text-muted-foreground">
                    {loading ? "Loading news…" : "No news items returned."}
                  </li>
                )}
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card p-6">
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">Reddit sentiment</div>
              <Badge tone="neutral">{sentimentSummary.reddit.total} posts</Badge>
            </div>
            <div className="mt-4 space-y-3">
              <SentimentBar label="Positive" value={sentimentSummary.reddit.positive} total={sentimentSummary.reddit.total} />
              <SentimentBar label="Neutral" value={sentimentSummary.reddit.neutral} total={sentimentSummary.reddit.total} />
              <SentimentBar label="Negative" value={sentimentSummary.reddit.negative} total={sentimentSummary.reddit.total} />
            </div>

            <div className="mt-6">
              <div className="text-sm font-medium">Sample posts</div>
              <ul className="mt-2 space-y-2">
                {(reddit ?? []).slice(0, 6).map((r, i) => {
                  const s = normalizeSentiment(r.sentiment);
                  return (
                    <li key={i} className="rounded-xl border border-border bg-white p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="text-sm leading-snug">{r.post}</div>
                        <Badge
                          tone={s === "positive" ? "good" : s === "negative" ? "bad" : "neutral"}
                        >
                          {s}
                        </Badge>
                      </div>
                    </li>
                  );
                })}
                {!reddit?.length && (
                  <li className="text-sm text-muted-foreground">
                    {loading ? "Loading posts…" : "No Reddit posts returned."}
                  </li>
                )}
              </ul>
            </div>
          </div>
        </section>

        {/* Financials */}
        <section className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-lg font-semibold">Key financials</div>
              <p className="mt-1 text-sm text-muted-foreground">
                We only show the most useful metrics first. Raw data is available below.
              </p>
            </div>

            {direction2 && confidence2 !== null ? (
              <Badge tone={toneFromDirection(direction2) as any}>
                Financial model: {direction2} ({(confidence2 * 100).toFixed(1)}%)
              </Badge>
            ) : null}
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {keyFinancials.map((kv) => (
              <div key={kv.label} className="rounded-xl border border-border bg-white p-4">
                <div className="text-sm text-muted-foreground">{kv.label}</div>
                <div className="mt-1 text-base font-semibold break-words">
                  {typeof kv.value === "number"
                    ? kv.label.toLowerCase().includes("margin") || kv.label === "ROE"
                      ? `${(kv.value * 100).toFixed(2)}%`
                      : kv.value.toLocaleString()
                    : String(kv.value)}
                </div>
              </div>
            ))}

            {!financials && (
              <div className="text-sm text-muted-foreground">
                {loading ? "Loading financials…" : "No financials returned."}
              </div>
            )}
          </div>

          {/* Raw + advanced */}
          <details className="mt-6 rounded-xl border border-border bg-white p-4">
            <summary className="cursor-pointer select-none font-medium">
              Advanced: raw financial JSON
            </summary>
            <pre className="mt-3 overflow-auto rounded-lg bg-black/5 p-4 text-xs">
              {financials ? JSON.stringify(financials, null, 2) : "—"}
            </pre>
          </details>
        </section>

        <section className="rounded-2xl border border-border bg-card p-6">
          <div className="font-medium">Reminder</div>
          <p className="mt-2 text-sm text-muted-foreground">
            This dashboard is not financial advice. Use it to summarize signals faster—not to replace research.
          </p>
        </section>
      </main>
    </div>
  );
}
