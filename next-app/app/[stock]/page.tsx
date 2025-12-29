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
  direction: string;
  confidence: number;
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

/** ---------- Financials helpers (5-stat comparison) ---------- */
function formatMoneyCompact(n: any) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "—";
  return (
    "$" +
    n.toLocaleString(undefined, {
      notation: "compact",
      maximumFractionDigits: 2,
    })
  );
}

function getVal(obj: any, key: string) {
  if (!obj) return undefined;
  if (obj[key] !== undefined && obj[key] !== null) return obj[key];

  const kLower = key.toLowerCase();
  const found = Object.keys(obj).find((k) => k.toLowerCase() === kLower);
  if (found) return obj[found];

  return undefined;
}

type MetricDef = {
  label: string;
  key: string;
  format: (n: any) => string;
};

const TOP_METRICS: MetricDef[] = [
  { label: "Revenue", key: "Total Revenue", format: formatMoneyCompact },
  { label: "Net Income", key: "Net Income", format: formatMoneyCompact },
  { label: "EBITDA", key: "EBITDA", format: formatMoneyCompact },
  {
    label: "Operating Income",
    key: "Total Operating Income As Reported",
    format: formatMoneyCompact,
  },
  {
    label: "Diluted EPS",
    key: "Diluted EPS",
    format: (n) => (typeof n === "number" ? n.toFixed(2) : "—"),
  },
];

function deltaText(latest: any, prev: any) {
  if (typeof latest !== "number" || typeof prev !== "number") return null;
  if (!Number.isFinite(latest) || !Number.isFinite(prev) || prev === 0) return null;
  const change = (latest - prev) / Math.abs(prev);
  const sign = change >= 0 ? "+" : "";
  return `${sign}${(change * 100).toFixed(1)}%`;
}

async function fetchJsonOrThrow(url: string, init?: RequestInit) {
  try {
    const res = await fetch(url, init);
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${url} -> ${res.status} ${res.statusText}${text ? ` | ${text}` : ""}`);
    }
    return res.json();
  } catch (e: any) {
    // This is where "Failed to fetch" usually ends up (CORS / network)
    throw new Error(`${url} -> ${e?.message ?? String(e)}`);
  }
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
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!T) return;

    const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    (async () => {
      setLoading(true);
      setError(null);
      setWarnings([]);

      const results = await Promise.allSettled([
        fetchJsonOrThrow(`${API}/predict?stock=${encodeURIComponent(T)}`),
        fetchJsonOrThrow(`${API}/api/news`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: T }),
        }),
        fetchJsonOrThrow(`${API}/api/reddit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: T }),
        }),
        fetchJsonOrThrow(`${API}/api/financials`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: T }),
        }),
      ]);

      const [predRes, newsRes, redditRes, finRes] = results;

      if (predRes.status === "fulfilled") setPrediction(predRes.value);
      else {
        setError(String(predRes.reason));
        setLoading(false);
        return;
      }

      const nextWarnings: string[] = [];

      if (newsRes.status === "fulfilled") setNews(newsRes.value?.news ?? []);
      else nextWarnings.push(String(newsRes.reason));

      if (redditRes.status === "fulfilled") setReddit(redditRes.value?.reddit ?? []);
      else nextWarnings.push(String(redditRes.reason));

      if (finRes.status === "fulfilled") {
        setFinancials(finRes.value?.financials ?? null);
        setDirection2(finRes.value?.direction ?? null);
        setConfidence2(finRes.value?.confidence ?? null);
      } else {
        nextWarnings.push(String(finRes.reason));
      }

      setWarnings(nextWarnings);
      setLoading(false);
    })();
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
            <p className="mt-3 text-xs text-muted-foreground">
              If this says “Failed to fetch”, it’s almost always CORS or the backend is not reachable.
              Open <span className="font-medium">http://localhost:8000/docs</span> to confirm backend is up.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const dir = prediction?.direction?.toUpperCase() ?? "—";
  const changePct = prediction?.predicted_change_pct ?? NaN;

  // ✅ your backend returns "prev", not "previous" :contentReference[oaicite:4]{index=4}
  const latestObj = (financials as any)?.latest;
  const prevObj = (financials as any)?.prev;

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
        {/* Warnings */}
        {warnings.length > 0 ? (
          <section className="rounded-2xl border border-border bg-card p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-semibold">Some data sources are unavailable</div>
                <div className="mt-1 text-sm text-muted-foreground">
                  The dashboard still loads with what’s available.
                </div>
              </div>
              <Badge tone="warn">Partial</Badge>
            </div>
            <ul className="mt-3 list-disc pl-5 text-sm text-muted-foreground space-y-1">
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {/* Top stats */}
        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Current Price" value={prediction ? money(prediction.current_price) : "—"} subvalue="Latest available price" />
          <StatCard
            title="Predicted Price"
            value={prediction ? money(prediction.predicted_price) : "—"}
            subvalue="Model estimate (next step)"
            badge={prediction ? { text: dir === "UP" ? "UP" : dir === "DOWN" ? "DOWN" : "—", tone: toneFromDirection(dir) as any } : undefined}
          />
          <StatCard
            title="Predicted Change"
            value={prediction ? pct(prediction.predicted_change_pct) : "—"}
            subvalue={prediction ? `Direction: ${dir}` : "—"}
            badge={prediction ? { text: prediction.system_confidence?.toUpperCase?.() ?? "—", tone: "neutral" } : undefined}
          />
          <StatCard
            title="Confidence"
            value={prediction ? `${(prediction.confidence * 100).toFixed(1)}%` : "—"}
            subvalue={prediction ? `Models: ${prediction.model_info.direction_model} + ${prediction.model_info.magnitude_model}` : "—"}
          />
        </section>

        {/* Confidence bar */}
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
            <div className="h-full bg-black" style={{ width: `${prediction ? Math.round(prediction.confidence * 100) : 0}%` }} />
          </div>

          <div className="mt-3 text-sm text-muted-foreground">
            System confidence:{" "}
            <span className="font-medium text-foreground">{prediction?.system_confidence?.toUpperCase?.() ?? "—"}</span>{" "}
            • Predicted move: <span className="font-medium text-foreground">{pct(changePct)}</span>
          </div>
        </section>

        {/* Sentiment */}
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
          </div>
        </section>

        {/* Financials */}
        <section className="rounded-2xl border border-border bg-card p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-lg font-semibold">Key financials</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Quick comparison (latest vs previous). Raw data is still available below.
              </p>
            </div>

            {direction2 && confidence2 !== null ? (
              <Badge tone={toneFromDirection(direction2) as any}>
                Financial model: {direction2} ({(confidence2 * 100).toFixed(1)}%)
              </Badge>
            ) : null}
          </div>

          <div className="mt-5 overflow-hidden rounded-2xl border border-border bg-white">
            <div className="grid grid-cols-12 gap-0 border-b border-border bg-black/5 px-4 py-3 text-xs font-medium text-muted-foreground">
              <div className="col-span-5">Metric</div>
              <div className="col-span-3 text-right">Latest</div>
              <div className="col-span-3 text-right">Previous</div>
              <div className="col-span-1 text-right">Δ</div>
            </div>

            <div className="divide-y divide-border">
              {TOP_METRICS.map((m) => {
                const latest = getVal(latestObj, m.key);
                const prev = getVal(prevObj, m.key);

                const latestStr = m.format(latest);
                const prevStr = m.format(prev);

                const d = deltaText(latest, prev);
                const dTone =
                  d && d.startsWith("+") ? "text-emerald-700" : d ? "text-rose-700" : "text-muted-foreground";

                return (
                  <div key={m.label} className="grid grid-cols-12 items-center px-4 py-3">
                    <div className="col-span-5">
                      <div className="text-sm font-medium">{m.label}</div>
                      <div className="text-xs text-muted-foreground">{m.key}</div>
                    </div>
                    <div className="col-span-3 text-right font-semibold tabular-nums">{latestStr}</div>
                    <div className="col-span-3 text-right text-muted-foreground tabular-nums">{prevStr}</div>
                    <div className={`col-span-1 text-right text-xs font-medium tabular-nums ${dTone}`}>{d ?? "—"}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <details className="mt-6 rounded-xl border border-border bg-white p-4">
            <summary className="cursor-pointer select-none font-medium">Advanced: raw financial JSON</summary>
            <pre className="mt-3 overflow-auto rounded-lg bg-black/5 p-4 text-xs">
              {financials ? JSON.stringify(financials, null, 2) : "—"}
            </pre>
          </details>
        </section>
      </main>
    </div>
  );
}
