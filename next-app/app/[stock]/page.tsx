"use client";

export const dynamic = "force-dynamic";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { Badge } from "../components/ui/Badge";
import { SentimentBar } from "../components/ui/SentimentBar";
import { StatCard } from "../components/ui/StatCard";
import { ThemeToggle } from "../components/ui/ThemeToggle";

type Tone = "neutral" | "good" | "bad" | "warn";

type SentimentCounts = {
  positive: number;
  negative: number;
  neutral: number;
  total: number;
};

type NewsItem = {
  headline: string;
  sentiment: string;
};

type LegacyFinancialResponse = {
  ticker: string;
  financials?: Record<string, unknown> | null;
  direction?: string | null;
  confidence?: number | null;
};

type MetricSnapshot = {
  latest: number | null;
  previous: number | null;
  change_pct: number | null;
};

type PredictionData = {
  direction: string;
  confidence: number;
  predicted_change_pct: number;
  predicted_price: number;
  current_price?: number | null;
  system_confidence: string;
  model_input_start_date?: string | null;
  model_input_end_date?: string | null;
  current_price_source?: string | null;
  current_price_session?: string | null;
  current_price_as_of?: string | null;
  price_delay_note?: string | null;
  model_info: {
    direction_model: string;
    magnitude_model: string;
    cached?: boolean;
  };
};

type CompanyData = {
  name?: string | null;
  ticker?: string | null;
  sector?: string | null;
  industry?: string | null;
  exchange?: string | null;
  current_price?: number | null;
  daily_change_pct?: number | null;
  market_cap?: number | null;
  links?: {
    yahoo_finance?: string | null;
    sec_search?: string | null;
  };
};

type PricePoint = {
  date: string;
  close: number;
  volume?: number | null;
  sma50?: number | null;
};

type PriceRange = {
  label: string;
  start_date: string;
  end_date: string;
  return_pct: number | null;
  high: number | null;
  low: number | null;
  points: PricePoint[];
};

type EarningsData = {
  reported_eps?: number | null;
  estimated_eps?: number | null;
  eps_change_pct?: number | null;
  reported_revenue?: number | null;
  revenue_change_pct?: number | null;
  recent_earnings_date?: string | null;
  next_earnings_date?: string | null;
  surprise?: {
    status: string;
    note?: string | null;
  };
};

type AnalysisData = {
  ticker: string;
  generated_at: string;
  company?: CompanyData | null;
  summary: {
    overall_score: number;
    verdict: string;
    key_points: string[];
    disclaimer: string;
  };
  price?: {
    current: number | null;
    previous_close: number | null;
    day_change_pct: number | null;
    currency: string;
    source?: string | null;
    session?: string | null;
    as_of?: string | null;
    is_realtime?: boolean;
    delay_note?: string | null;
  } | null;
  price_history?: {
    available_ranges: string[];
    ranges: Record<string, PriceRange>;
    history_last_trading_date?: string | null;
    history_cache_as_of?: string | null;
    trend_calculation_as_of?: string | null;
    quote_as_of?: string | null;
    stale_completed_trading_days?: number | null;
    confidence?: string | null;
    warnings?: string[];
  } | null;
  trend?: {
    label: string;
    score: number;
    returns: Record<string, number | null>;
    moving_averages: Record<string, number | boolean | null>;
  } | null;
  volume_liquidity?: {
    score: number;
    latest_volume: number | null;
    avg_volume_20d: number | null;
    volume_ratio: number | null;
    volume_signal: string;
  } | null;
  prediction?: PredictionData | null;
  news: {
    items: NewsItem[];
    sentiment_counts: SentimentCounts;
  };
  financials?: {
    highlights: Record<string, MetricSnapshot>;
    margins?: Record<string, number | null>;
    model?: {
      direction: string | null;
      confidence: number | null;
      available?: boolean;
      error?: string;
      name?: string;
    };
    source?: string;
    errors?: string[];
    score: number;
  } | null;
  earnings?: EarningsData | null;
  valuation?: {
    label: string;
    score: number;
    fair_value?: {
      current_price: number | null;
      estimated_fair_value: number | null;
      margin_of_safety_pct: number | null;
      verdict: string;
      estimates: Record<string, number | null>;
      assumptions: Record<string, number | string | null>;
      blended_reference_value?: number | null;
      intrinsic_estimates?: Record<string, number | null>;
      analyst_reference?: number | null;
      dcf_breakdown?: Record<string, number | string | boolean | string[] | null>;
      equation: string;
    };
    metrics: Record<string, number | string | null>;
    note: string;
  } | null;
  balance_sheet?: {
    score: number;
    period_end?: string | null;
    source?: string | null;
    warnings?: string[];
    metrics: Record<string, number | string | null>;
    strengths: string[];
    concerns: string[];
  } | null;
  dividend?: {
    score: number;
    label: string;
    metrics: Record<string, number | null>;
  } | null;
  analyst?: {
    score: number;
    recommendation?: string | null;
    metrics: Record<string, number | null>;
  } | null;
  risk?: {
    score: number;
    risk_level?: number;
    risk_safety_score?: number;
    factors: string[];
    components?: Array<Record<string, number | string | null>>;
  } | null;
  scores: {
    overall: number;
    trend: number;
    fundamentals: number;
    valuation: number;
    liquidity: number;
    risk: number;
    balance_sheet?: number;
    dividend?: number;
    analyst?: number;
  };
  score_model?: {
    version: string;
    weights: Record<string, number>;
    method: string;
  };
  reddit?: {
    disabled: boolean;
    reason: string;
  };
  data_quality: {
    sources: string[];
    warnings: string[];
    cache?: {
      status: string;
      ttl_seconds?: number;
      storage?: string;
      version?: string;
    };
  };
};

function money(n: number | null | undefined) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "-";
  return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function compact(n: number | null | undefined) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "-";
  return n.toLocaleString(undefined, { notation: "compact", maximumFractionDigits: 2 });
}

function pct(n: number | null | undefined) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "-";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function numberText(n: number | string | null | undefined) {
  if (typeof n === "string") return n || "-";
  if (typeof n !== "number" || !Number.isFinite(n)) return "-";
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function confidenceText(n: number | null | undefined) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "Provider did not return confidence.";
  return `${(n * 100).toFixed(1)}% model-provided confidence value`;
}

function sourceLabel(value: string | null | undefined) {
  if (!value) return "Free Yahoo/yfinance";
  return value.replace(/^yfinance_/, "yfinance ").replace(/_/g, " ");
}

function predictionModelNames(info: PredictionData["model_info"] | null | undefined) {
  const names = [info?.direction_model, info?.magnitude_model].filter((name): name is string => Boolean(name));
  const unique = Array.from(new Set(names));
  return unique.length ? unique.join(" + ") : "Unavailable";
}

function predictionModelRoleText(info: PredictionData["model_info"] | null | undefined) {
  if (!info?.direction_model && !info?.magnitude_model) return "Model names unavailable";
  return info.direction_model === info.magnitude_model ? "Direction and magnitude model" : "Direction model + magnitude model";
}
function dateText(value: string | null | undefined) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function dateTimeText(value: string | null | undefined) {
  if (!value) return "Unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function describeChange(label: string, value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return `${label} data is unavailable.`;
  if (value > 2) return `${label} increased from the previous annual period.`;
  if (value < -2) return `${label} declined from the previous annual period.`;
  return `${label} was roughly flat versus the previous annual period.`;
}

function scoreTone(score: number | null | undefined): Tone {
  if (typeof score !== "number") return "neutral";
  if (score >= 65) return "good";
  if (score <= 40) return "bad";
  return "warn";
}

function directionTone(direction: string | null | undefined): Tone {
  const d = (direction ?? "").toUpperCase();
  if (d === "UP" || d === "BULLISH") return "good";
  if (d === "DOWN" || d === "BEARISH") return "bad";
  return "neutral";
}

function sentimentCountsFromItems(items: NewsItem[]): SentimentCounts {
  const counts = { positive: 0, negative: 0, neutral: 0, total: 0 };
  for (const item of items) {
    const sentiment = String(item.sentiment ?? "").toLowerCase();
    if (sentiment.includes("pos")) counts.positive += 1;
    else if (sentiment.includes("neg")) counts.negative += 1;
    else counts.neutral += 1;
    counts.total += 1;
  }
  return counts;
}

function changeTone(value: number | null | undefined, goodWhenPositive = true): Tone {
  if (typeof value !== "number" || !Number.isFinite(value)) return "neutral";
  const directional = goodWhenPositive ? value : -value;
  if (directional > 2) return "good";
  if (directional < -2) return "bad";
  return "warn";
}

function metricLabel(key: string) {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function MetricTile({
  title,
  value,
  subvalue,
}: {
  title: string;
  value: React.ReactNode;
  subvalue?: React.ReactNode;
}) {
  return (
    <div className="rounded-md bg-subtle p-4">
      <div className="text-sm font-medium text-muted-foreground">{title}</div>
      <div className="mt-2 text-xl font-semibold tracking-tight">{value}</div>
      {subvalue ? <div className="mt-1 text-sm text-muted-foreground">{subvalue}</div> : null}
    </div>
  );
}

function EmptySection({ message }: { message: string }) {
  return <div className="rounded-lg border border-dashed border-border bg-card p-5 text-sm text-muted-foreground">{message}</div>;
}

function SectionNotice({
  title,
  message,
}: {
  title: string;
  message: string;
}) {
  return (
    <div className="rounded-md border border-border bg-subtle p-4 text-sm">
      <div className="font-medium">{title}</div>
      <div className="mt-1 text-muted-foreground">{message}</div>
    </div>
  );
}

function PriceChart({ range }: { range: PriceRange | undefined }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const chart = useMemo(() => {
    const points = range?.points.filter((point) => Number.isFinite(point.close)) ?? [];
    if (points.length < 2) return null;
    const width = 720;
    const height = 240;
    const pad = { top: 16, right: 14, bottom: 28, left: 48 };
    const values = points.flatMap((point) => [point.close, point.sma50]).filter((value): value is number => typeof value === "number" && Number.isFinite(value));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const x = (index: number) => pad.left + (index / (points.length - 1)) * (width - pad.left - pad.right);
    const y = (value: number) => pad.top + ((max - value) / span) * (height - pad.top - pad.bottom);
    return {
      width,
      height,
      pad,
      points,
      x,
      y,
      ticks: [max, min + span * 0.5, min],
      closeLine: points.map((point, index) => `${x(index)},${y(point.close)}`).join(" "),
      smaLine: points
        .map((point, index) => (typeof point.sma50 === "number" ? `${x(index)},${y(point.sma50)}` : null))
        .filter(Boolean)
        .join(" "),
    };
  }, [range]);

  if (!chart) return <EmptySection message="Historical prices are unavailable for this range." />;

  const index = activeIndex ?? chart.points.length - 1;
  const active = chart.points[index];

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3 text-sm">
        <div className="font-medium">Close price</div>
        <div className="text-muted-foreground">{dateText(active.date)} - {money(active.close)}</div>
      </div>
      <svg
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        className="h-72 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label="Historical closing price chart"
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          const ratio = (event.clientX - rect.left) / rect.width;
          setActiveIndex(Math.round(Math.max(0, Math.min(1, ratio)) * (chart.points.length - 1)));
        }}
        onMouseLeave={() => setActiveIndex(null)}
      >
        <rect width={chart.width} height={chart.height} className="chart-bg" />
        {chart.ticks.map((tick) => (
          <g key={tick}>
            <line x1={chart.pad.left} x2={chart.width - chart.pad.right} y1={chart.y(tick)} y2={chart.y(tick)} className="chart-grid" />
            <text x="4" y={chart.y(tick) + 4} className="chart-text" fontSize="12">{money(tick)}</text>
          </g>
        ))}
        {chart.smaLine ? <polyline points={chart.smaLine} fill="none" className="chart-average" strokeWidth="2" vectorEffect="non-scaling-stroke" /> : null}
        <polyline points={chart.closeLine} fill="none" className="chart-close" strokeWidth="3" vectorEffect="non-scaling-stroke" />
        <line x1={chart.x(index)} x2={chart.x(index)} y1={chart.pad.top} y2={chart.height - chart.pad.bottom} stroke="#111" strokeOpacity="0.18" vectorEffect="non-scaling-stroke" />
        <circle cx={chart.x(index)} cy={chart.y(active.close)} r="5" className="chart-point" stroke="white" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        <text x={chart.pad.left} y={chart.height - 8} className="chart-text" fontSize="12">{dateText(chart.points[0].date)}</text>
        <text x={chart.width - chart.pad.right - 92} y={chart.height - 8} className="chart-text" fontSize="12">{dateText(chart.points[chart.points.length - 1].date)}</text>
      </svg>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span>Green: close</span>
        <span>Amber: 50-day average when available</span>
        <span>Volume: {compact(active.volume)}</span>
      </div>
    </div>
  );
}

function ScoreBar({
  label,
  score,
  weight,
}: {
  label: string;
  score: number | null | undefined;
  weight?: number;
}) {
  const value = typeof score === "number" && Number.isFinite(score) ? Math.round(score) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">
          {value}/100{typeof weight === "number" ? ` - ${Math.round(weight * 100)}%` : ""}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-subtle">
        <div className="h-full bg-foreground" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}


async function fetchJsonOrThrow<T = AnalysisData>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const raw = await res.text().catch(() => "");
    let message = raw;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // Keep the raw response text when the server does not return JSON.
    }
    throw new Error(`${res.status} ${res.statusText}${message ? ` - ${message}` : ""}`);
  }
  return (await res.json()) as T;
}

export default function StockPage() {
  const params = useParams();
  const raw = params.stock;
  const ticker = Array.isArray(raw) ? raw[0] ?? "" : raw ?? "";
  const T = ticker.toUpperCase();

  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [legacyPrediction, setLegacyPrediction] = useState<PredictionData | null>(null);
  const [legacyNews, setLegacyNews] = useState<NewsItem[]>([]);
  const [legacyFinancial, setLegacyFinancial] = useState<LegacyFinancialResponse | null>(null);
  const [legacyWarnings, setLegacyWarnings] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [legacyLoading, setLegacyLoading] = useState(false);
  const [activeRange, setActiveRange] = useState("1y");

  useEffect(() => {
    if (!T) return;

    const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";
    let cancelled = false;

    (async () => {
      setLoading(true);
      setError(null);
      setAnalysis(null);

      try {
        const data = await fetchJsonOrThrow(`${API}/analysis?stock=${encodeURIComponent(T)}`);
        if (!cancelled) setAnalysis(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [T]);

  useEffect(() => {
    if (!T) return;

    const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";
    let cancelled = false;

    (async () => {
      setLegacyLoading(true);
      setLegacyPrediction(null);
      setLegacyNews([]);
      setLegacyFinancial(null);
      setLegacyWarnings([]);

      const results = await Promise.allSettled([
        fetchJsonOrThrow<PredictionData>(`${API}/predict?stock=${encodeURIComponent(T)}`),
        fetchJsonOrThrow<{ ticker: string; news?: NewsItem[] }>(`${API}/api/news`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: T }),
        }),
        fetchJsonOrThrow<LegacyFinancialResponse>(`${API}/api/financials`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker: T }),
        }),
      ]);

      if (cancelled) return;

      const warnings: string[] = [];
      const [predictionResult, newsResult, financialResult] = results;

      if (predictionResult.status === "fulfilled") setLegacyPrediction(predictionResult.value);
      else warnings.push(`/predict failed: ${predictionResult.reason instanceof Error ? predictionResult.reason.message : String(predictionResult.reason)}`);

      if (newsResult.status === "fulfilled") setLegacyNews(newsResult.value.news ?? []);
      else warnings.push(`/api/news failed: ${newsResult.reason instanceof Error ? newsResult.reason.message : String(newsResult.reason)}`);

      if (financialResult.status === "fulfilled") setLegacyFinancial(financialResult.value);
      else warnings.push(`/api/financials failed: ${financialResult.reason instanceof Error ? financialResult.reason.message : String(financialResult.reason)}`);

      setLegacyWarnings(warnings);
      setLegacyLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [T]);
  const financialRows = useMemo(() => {
    const highlights = analysis?.financials?.highlights;
    if (!highlights) return [];
    const preferred = [
      "revenue",
      "eps",
      "net_income",
      "operating_income",
      "operating_cash_flow",
      "free_cash_flow",
      "total_debt",
      "cash",
    ];
    return preferred
      .filter((key) => highlights[key])
      .map((key) => ({ key, value: highlights[key] }));
  }, [analysis]);

  const snapshotItems = useMemo(() => {
    if (!analysis) return [];
    const items: Array<{ title: string; value: string; detail: string; tone: Tone }> = [];
    const highlights = analysis.financials?.highlights ?? {};
    const revenue = highlights.revenue;
    const netIncome = highlights.net_income;
    const eps = highlights.eps;
    const fcf = highlights.free_cash_flow;

    if (revenue) {
      items.push({
        title: "Revenue Trend",
        value: describeChange("Revenue", revenue.change_pct),
        detail: `${compact(revenue.latest)} latest available annual revenue`,
        tone: changeTone(revenue.change_pct),
      });
    }

    const earningsMetric = netIncome ?? eps;
    if (earningsMetric) {
      items.push({
        title: netIncome ? "Earnings Trend" : "EPS Trend",
        value: describeChange(netIncome ? "Net income" : "EPS", earningsMetric.change_pct),
        detail: `${netIncome ? compact(earningsMetric.latest) : numberText(earningsMetric.latest)} latest available annual value`,
        tone: changeTone(earningsMetric.change_pct),
      });
    }

    const operatingMargin = analysis.financials?.margins?.operating_margin_pct;
    if (typeof operatingMargin === "number" && Number.isFinite(operatingMargin)) {
      items.push({
        title: "Profitability",
        value: `Operating margin is ${pct(operatingMargin)}.`,
        detail: "Rule-based margin observation",
        tone: operatingMargin >= 15 ? "good" : operatingMargin >= 5 ? "warn" : "bad",
      });
    }

    if (fcf && typeof fcf.latest === "number") {
      items.push({
        title: "Cash Flow",
        value: fcf.latest > 0 ? "Free cash flow is positive." : "Free cash flow is negative.",
        detail: `${compact(fcf.latest)} latest available annual free cash flow`,
        tone: fcf.latest > 0 ? "good" : "bad",
      });
    }

    if (analysis.risk?.factors?.length) {
      items.push({
        title: "Risk Indicator",
        value: analysis.risk.factors[0],
        detail: `${analysis.risk.score}/100 quantitative risk score`,
        tone: scoreTone(analysis.risk.score),
      });
    }

    if (analysis.prediction) {
      items.push({
        title: "Quantitative Signal",
        value: `Existing model reports ${analysis.prediction.direction}.`,
        detail: `${pct(analysis.prediction.predicted_change_pct)} implied move`,
        tone: directionTone(analysis.prediction.direction),
      });
    }

    return items.slice(0, 6);
  }, [analysis]);

  if (error) {
    return (
      <div className="min-h-screen bg-bg">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
            Back
          </Link>
          <div className="mt-6 rounded-lg border border-border bg-card p-6">
            <div className="text-lg font-semibold">Analysis failed</div>
            <p className="mt-2 text-sm text-muted-foreground">{error}</p>
            <p className="mt-3 text-xs text-muted-foreground">
              Check that the backend is running at http://127.0.0.1:8001 and try
              http://127.0.0.1:8001/analysis?stock={T}.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const score = analysis?.summary.overall_score ?? 0;
  const trend = analysis?.trend;
  const valuation = analysis?.valuation;
  const fairValue = valuation?.fair_value;
  const dcfBreakdown = fairValue?.dcf_breakdown;
  const balanceSheet = analysis?.balance_sheet;
  const dividend = analysis?.dividend;
  const analyst = analysis?.analyst;
  const weights = analysis?.score_model?.weights ?? {};
  const prediction = analysis?.prediction;
  const company = analysis?.company;
  const earnings = analysis?.earnings;
  const margins = analysis?.financials?.margins ?? {};
  const priceHistory = analysis?.price_history;
  const availableRanges = priceHistory?.available_ranges ?? [];
  const selectedRangeKey = availableRanges.includes(activeRange) ? activeRange : availableRanges.includes("1y") ? "1y" : availableRanges[0];
  const selectedRange = selectedRangeKey ? priceHistory?.ranges[selectedRangeKey] : undefined;
  const newsItems = analysis?.news?.items ?? [];
  const newsCounts = analysis?.news?.sentiment_counts ?? {
    positive: 0,
    negative: 0,
    neutral: 0,
    total: 0,
  };
  const previousPrediction = legacyPrediction ?? prediction;
  const previousNewsItems = legacyNews.length ? legacyNews : newsItems;
  const previousNewsCounts = legacyNews.length ? sentimentCountsFromItems(legacyNews) : newsCounts;
  const previousFinancialDirection = legacyFinancial?.direction ?? analysis?.financials?.model?.direction;
  const previousFinancialConfidence = legacyFinancial?.confidence ?? analysis?.financials?.model?.confidence;
  const scoreEntries = [
    { key: "valuation", label: "Valuation", score: analysis?.scores.valuation, weight: weights.valuation },
    { key: "fundamentals", label: "Fundamentals", score: analysis?.scores.fundamentals, weight: weights.fundamentals },
    { key: "trend", label: "Trend", score: analysis?.scores.trend, weight: weights.trend },
    { key: "balance", label: "Balance sheet", score: analysis?.scores.balance_sheet, weight: weights.balance_sheet },
    { key: "risk", label: "Risk", score: analysis?.scores.risk, weight: weights.risk },
    { key: "liquidity", label: "Liquidity", score: analysis?.scores.liquidity, weight: weights.liquidity },
    { key: "analyst", label: "Analyst", score: analysis?.scores.analyst, weight: weights.analyst },
  ];
  const rankedScores = [...scoreEntries]
    .filter((entry) => typeof entry.score === "number")
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
  const topDrivers = rankedScores.slice(0, 3);
  const weakDrivers = [...rankedScores].reverse().slice(0, 3);
  const actionLabel = score >= 70 ? "Research candidate" : score >= 50 ? "Watchlist / compare" : "High caution";
  const yahooLink = company?.links?.yahoo_finance ?? `https://finance.yahoo.com/quote/${T}`;
  const secLink = company?.links?.sec_search ?? `https://www.sec.gov/edgar/search/#/q=${T}`;
  const warnings = analysis?.data_quality?.warnings ?? [];
  const warningFor = (section: string) => warnings.find((warning) => warning.toLowerCase().includes(section));
  const predictionWarning = legacyWarnings.find((warning) => warning.includes("/predict")) ?? warningFor("prediction");
  const newsWarning = legacyWarnings.find((warning) => warning.includes("/api/news")) ?? warningFor("news");
  const financialWarning = legacyWarnings.find((warning) => warning.includes("/api/financials")) ?? analysis?.financials?.model?.error ?? analysis?.financials?.errors?.join(" ");
  const priceSession = sourceLabel(analysis?.price?.session);
  const priceSource = sourceLabel(analysis?.price?.source);
  const priceAsOf = analysis?.price?.as_of ? dateTimeText(analysis.price.as_of) : "latest free quote";
  const priceDelayNote = analysis?.price?.delay_note ?? "Free price quotes may be delayed or unavailable; verify real-time prices with an exchange or brokerage before trading.";

  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-border bg-card backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
              Back
            </Link>
            <div className="h-6 w-px bg-border" />
            <div>
              <div className="text-sm text-muted-foreground">Research dashboard</div>
              <div className="text-xl font-semibold tracking-tight">{company?.name ?? T}</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Badge tone={analysis ? scoreTone(score) : "neutral"}>
              {loading ? "Loading..." : analysis?.summary.verdict ?? "No data"}
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
        {loading && !analysis ? (
          <section className="rounded-lg border border-border bg-card p-6">
            <div className="text-lg font-semibold">Building research dashboard for {T}</div>
            <p className="mt-2 text-sm text-muted-foreground">
              Loading available price history, financial data, earnings context, risk indicators, and the existing quantitative signal. Optional sections may appear as unavailable.
            </p>
          </section>
        ) : null}

        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Overall Score"
            value={analysis ? `${score}/100` : "-"}
            subvalue={analysis?.summary.verdict ?? "Waiting for analysis"}
            badge={analysis ? { text: analysis.summary.verdict, tone: scoreTone(score) } : undefined}
          />
          <StatCard
            title="Current Price"
            value={money(analysis?.price?.current)}
            subvalue={analysis ? `${priceSession}: ${pct(analysis.price?.day_change_pct)} as of ${priceAsOf}` : "Latest free quote"}
          />
          <StatCard
            title="Trend"
            value={trend?.label ?? "-"}
            subvalue={trend ? `${trend.score}/100 trend score` : "Price and moving averages"}
            badge={trend ? { text: `${trend.score}`, tone: scoreTone(trend.score) } : undefined}
          />
          <StatCard
            title="Valuation"
            value={valuation?.label ?? "-"}
            subvalue={valuation ? `${valuation.score}/100 valuation score` : "Basic valuation screen"}
            badge={valuation ? { text: `${valuation.score}`, tone: scoreTone(valuation.score) } : undefined}
          />
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-4xl font-semibold tracking-tight">{company?.ticker ?? T}</h1>
                {company?.sector ? <Badge tone="neutral">{company.sector}</Badge> : null}
                {company?.exchange ? <Badge tone="neutral">{company.exchange}</Badge> : null}
              </div>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
                {company?.industry ?? "Industry data unavailable."} The dashboard separates objective data, rule-based observations, and the existing experimental prediction signal.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <ThemeToggle />
              <a href={yahooLink} target="_blank" rel="noreferrer noopener" className="rounded-md border border-border bg-subtle px-3 py-2 text-sm font-medium text-foreground hover:bg-surface">
                Yahoo Finance
              </a>
              <a href={secLink} target="_blank" rel="noreferrer noopener" className="rounded-md border border-border bg-subtle px-3 py-2 text-sm font-medium text-foreground hover:bg-surface">
                SEC filings
              </a>
            </div>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricTile title="Company" value={company?.name ?? T} subvalue={company?.industry ?? "Profile unavailable"} />
            <MetricTile title="Market Cap" value={compact(company?.market_cap)} subvalue="Free Yahoo profile data" />
            <MetricTile title="Last Updated" value={dateTimeText(analysis?.generated_at)} subvalue="Backend analysis timestamp" />
            <MetricTile title="Price Source" value={priceSource} subvalue={`Market data as of ${priceAsOf}`} />
            <MetricTile title="Structured Data" value="Ready" subvalue="Reusable Phase 1 snapshot endpoint" />
          </div>
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-lg font-semibold">Research snapshot</div>
              <p className="mt-1 text-sm text-muted-foreground">Rule-based observations from available reported data and calculated signals.</p>
            </div>
          </div>
          {snapshotItems.length ? (
            <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {snapshotItems.map((item) => (
                <div key={item.title} className="rounded-lg border border-border bg-subtle p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm font-medium text-muted-foreground">{item.title}</div>
                    <Badge tone={item.tone}>Rule-based</Badge>
                  </div>
                  <div className="mt-3 text-base font-semibold leading-snug">{item.value}</div>
                  <div className="mt-2 text-sm text-muted-foreground">{item.detail}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="mt-5">
              <EmptySection message="Snapshot observations are unavailable until the dashboard receives enough financial, price, or model data." />
            </div>
          )}
        </section>

        <section className="rounded-lg border border-border bg-card p-6">
          <div className="grid gap-6 lg:grid-cols-[1.1fr_1.4fr_1fr]">
            <div>
              <div className="text-sm font-medium text-muted-foreground">Dashboard verdict</div>
              <div className="mt-3 flex items-end gap-3">
                <div className="text-6xl font-semibold tracking-tight tabular-nums">{analysis ? score : "-"}</div>
                <div className="pb-2 text-sm text-muted-foreground">/100</div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge tone={scoreTone(score)}>{analysis?.summary.verdict ?? "Loading"}</Badge>
                <Badge tone="neutral">{actionLabel}</Badge>
              </div>
              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                This page is now organized as an analysis workflow: verdict first, drivers next, then valuation, fundamentals, balance sheet, risk, and supporting signals.
              </p>
            </div>

            <div>
              <div className="flex items-center justify-between gap-3">
                <div className="text-lg font-semibold">Main drivers</div>
                {analysis?.reddit?.disabled ? <Badge tone="warn">Reddit disabled</Badge> : null}
              </div>
              <div className="mt-4 divide-y divide-border rounded-md border border-border bg-card">
                {(analysis?.summary.key_points ?? ["Loading analysis..."]).map((point, index) => (
                  <div key={index} className="px-4 py-3 text-sm leading-relaxed">
                    {point}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="text-lg font-semibold">Strongest / weakest</div>
              <div className="mt-4 space-y-4">
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">Strongest</div>
                  <div className="mt-2 space-y-2">
                    {topDrivers.map((driver) => (
                      <div key={driver.key} className="flex items-center justify-between gap-3 text-sm">
                        <span>{driver.label}</span>
                        <Badge tone={scoreTone(driver.score)}>{Math.round(driver.score ?? 0)}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">Needs review</div>
                  <div className="mt-2 space-y-2">
                    {weakDrivers.map((driver) => (
                      <div key={driver.key} className="flex items-center justify-between gap-3 text-sm">
                        <span>{driver.label}</span>
                        <Badge tone={scoreTone(driver.score)}>{Math.round(driver.score ?? 0)}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {analysis?.data_quality?.warnings?.length ? (
            <div className="mt-6 rounded-md border border-amber-200 bg-amber-500/10 p-4">
              <div className="font-medium text-amber-900">Some data sources failed</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
                {analysis.data_quality.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>

        <nav className="sticky top-0 z-10 -mx-6 border-y border-border bg-bg px-6 py-3 backdrop-blur">
          <div className="mx-auto flex max-w-6xl gap-2 overflow-x-auto text-sm">
            <a href="#score" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Score</a>
            <a href="#market" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Price</a>
            <a href="#fundamentals" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Financials</a>
            <a href="#earnings" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Earnings</a>
            <a href="#risk" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Risk</a>
            <a href="#signals" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Signals</a>
            <a href="#ai-assistant" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">AI assistant</a>
            <a href="#previous-predictions" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Previous predictions</a>
            <a href="#sources" className="whitespace-nowrap rounded-md border border-border bg-card px-3 py-2 hover:bg-subtle">Sources</a>
          </div>
        </nav>

        <section id="score" className="grid gap-4 lg:grid-cols-3 scroll-mt-20">
          <div className="rounded-lg border border-border bg-card p-6 lg:col-span-2">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold">Score breakdown</div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Weighted Phase 1 research snapshot. Higher means the rule-based signal is stronger.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone={scoreTone(score)}>{analysis?.score_model?.version ?? "phase-1"}</Badge>
              </div>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <ScoreBar label="Valuation" score={analysis?.scores.valuation} weight={weights.valuation} />
              <ScoreBar label="Fundamentals" score={analysis?.scores.fundamentals} weight={weights.fundamentals} />
              <ScoreBar label="Trend" score={analysis?.scores.trend} weight={weights.trend} />
              <ScoreBar label="Balance sheet" score={analysis?.scores.balance_sheet} weight={weights.balance_sheet} />
              <ScoreBar label="Risk" score={analysis?.scores.risk} weight={weights.risk} />
              <ScoreBar label="Liquidity" score={analysis?.scores.liquidity} weight={weights.liquidity} />
              <ScoreBar label="Analyst" score={analysis?.scores.analyst} weight={weights.analyst} />
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <div className="text-lg font-semibold">Blended value reference</div>
            <div className="mt-3 text-3xl font-semibold">{money(fairValue?.blended_reference_value ?? fairValue?.estimated_fair_value)}</div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge tone={scoreTone(valuation?.score)}>{valuation?.label ?? "Unknown"}</Badge>
              <Badge tone={scoreTone(valuation?.score)}>{pct(fairValue?.margin_of_safety_pct)} margin</Badge>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              {fairValue?.equation ?? "Fair value needs more data."}
            </p>
          </div>
        </section>

        <section id="market" className="grid gap-4 lg:grid-cols-3 scroll-mt-20">
          <div className="rounded-lg border border-border bg-card p-6 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold">Price performance</div>
                <p className="mt-1 text-sm text-muted-foreground">Historical close with 50-day moving average when available.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableRanges.map((range) => (
                  <button
                    key={range}
                    type="button"
                    onClick={() => setActiveRange(range)}
                    className={`rounded-md border px-3 py-2 text-sm font-medium ${selectedRangeKey === range ? "border-emerald-700 bg-emerald-600 text-white" : "border-border bg-subtle text-foreground hover:bg-surface"}`}
                  >
                    {range.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>
            <div className="mt-5">
              <PriceChart range={selectedRange} />
            </div>
            <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricTile title="Range Return" value={pct(selectedRange?.return_pct)} subvalue={`${dateText(selectedRange?.start_date)} to ${dateText(selectedRange?.end_date)}`} />
              <MetricTile title="History Through" value={dateText(analysis?.price_history?.history_last_trading_date)} subvalue={`${analysis?.price_history?.confidence ?? "unknown"} history confidence`} />
              <MetricTile title="Avg Volume" value={compact(analysis?.volume_liquidity?.avg_volume_20d)} subvalue="20-day average" />
              <MetricTile title="Trend As Of" value={analysis?.price_history?.trend_calculation_as_of ? dateTimeText(analysis.price_history.trend_calculation_as_of) : "Unavailable"} subvalue={analysis?.price_history?.warnings?.[0] ?? "Same dataset as chart and moving averages"} />
            </div>
          </div>

          <div id="risk" className="rounded-lg border border-border bg-card p-6 scroll-mt-20">
            <div className="flex items-center justify-between gap-3">
              <div className="text-lg font-semibold">Risk indicators</div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <div className="text-3xl font-semibold">{analysis?.risk?.risk_safety_score ?? analysis?.risk?.score ?? "-"}</div>
              <Badge tone={scoreTone(analysis?.risk?.risk_safety_score ?? analysis?.risk?.score)}>Risk safety score</Badge>
              <Badge tone="warn">Risk level {analysis?.risk?.risk_level ?? "-"}</Badge>
            </div>
            <div className="mt-4 space-y-2 text-sm text-muted-foreground">
              {(analysis?.risk?.factors?.length ? analysis.risk.factors : ["Risk data is limited for this ticker."]).map(
                (factor, index) => (
                  <div key={index}>{factor}</div>
                )
              )}
            </div>
          </div>
        </section>

        <section id="fundamentals" className="grid gap-4 lg:grid-cols-2 scroll-mt-20">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-lg font-semibold">Financial performance</div>
                <div className="mt-1 text-sm text-muted-foreground">Reported fundamentals, simplified for dashboard review.</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <a href={yahooLink} target="_blank" rel="noreferrer noopener" className="rounded-md border border-border bg-subtle px-3 py-2 text-sm font-medium text-foreground hover:bg-surface">Full report</a>
                {analysis?.financials ? (
                  <Badge tone={scoreTone(analysis.financials.score)}>{analysis.financials.score}/100</Badge>
                ) : null}
              </div>
            </div>
            <div className="mt-5 overflow-x-auto rounded-lg border border-border bg-card">
              <div className="min-w-[640px]">
                <div className="grid grid-cols-12 border-b border-border bg-subtle px-4 py-3 text-xs font-medium text-muted-foreground">
                  <div className="col-span-4">Metric</div>
                  <div className="col-span-3 text-right">Latest available</div>
                  <div className="col-span-3 text-right">Previous annual</div>
                  <div className="col-span-2 text-right">Change</div>
                </div>
                <div className="divide-y divide-border">
                  {financialRows.length ? (
                    financialRows.map((row) => (
                      <div key={row.key} className="grid grid-cols-12 px-4 py-3 text-sm">
                        <div className="col-span-4 font-medium">{metricLabel(row.key)}</div>
                        <div className="col-span-3 text-right tabular-nums">
                          {row.key === "eps" ? numberText(row.value.latest) : compact(row.value.latest)}
                        </div>
                        <div className="col-span-3 text-right tabular-nums text-muted-foreground">
                          {row.key === "eps" ? numberText(row.value.previous) : compact(row.value.previous)}
                        </div>
                        <div className="col-span-2 text-right tabular-nums">{pct(row.value.change_pct)}</div>
                      </div>
                    ))
                  ) : (
                    <div className="px-4 py-5 text-sm text-muted-foreground">Financial data is unavailable from the free providers for this ticker.</div>
                  )}
                </div>
              </div>
            </div>
            {analysis?.financials?.errors?.length ? (
              <div className="mt-4 rounded-md border border-amber-200 bg-amber-500/10 p-4 text-sm text-amber-900">
                Some financial data was partial: {analysis.financials.errors.join(" ")}
              </div>
            ) : null}
            {financialRows.length ? (
              <>
                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                  <MetricTile title="Gross Margin" value={pct(margins.gross_margin_pct)} subvalue="Gross profit / revenue" />
                  <MetricTile title="Operating Margin" value={pct(margins.operating_margin_pct)} subvalue="Operating income / revenue" />
                  <MetricTile title="Free Cash Flow Margin" value={pct(margins.free_cash_flow_margin_pct)} subvalue="FCF / revenue" />
                </div>
                <div className="mt-4 rounded-md bg-subtle p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-medium">Financial statement model</div>
                    {analysis?.financials?.model?.direction ? (
                      <Badge tone={directionTone(analysis.financials.model.direction)}>{analysis.financials.model.direction}</Badge>
                    ) : (
                      <Badge tone="neutral">Unavailable</Badge>
                    )}
                  </div>
                  <div className="mt-2 text-muted-foreground">
                    {typeof analysis?.financials?.model?.confidence === "number"
                      ? confidenceText(analysis.financials.model.confidence)
                      : analysis?.financials?.model?.error ?? "Waiting for enough financial statement data."}
                  </div>
                  {analysis?.financials?.source ? (
                    <div className="mt-1 text-xs text-muted-foreground">Source: {analysis.financials.source}</div>
                  ) : null}
                </div>
              </>
            ) : (
              <div className="mt-4">
                <SectionNotice
                  title="Financial model unavailable"
                  message="The dashboard keeps running when statement data is missing. Use the full-report link for external research."
                />
              </div>
            )}
          </div>

          <div id="valuation" className="rounded-lg border border-border bg-card p-6 scroll-mt-20">
            <div className="flex items-center justify-between gap-3">
              <div className="text-lg font-semibold">Valuation screen</div>
              {valuation ? <Badge tone={scoreTone(valuation.score)}>{valuation.score}/100</Badge> : null}
            </div>
            {valuation ? (
              <>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <MetricTile title="Blended Reference" value={money(fairValue?.blended_reference_value ?? fairValue?.estimated_fair_value)} subvalue="DCF, EPS model, and analyst target" />
                  <MetricTile title="Reference Margin" value={pct(fairValue?.margin_of_safety_pct)} subvalue="Blended reference versus price" />
                  <MetricTile title="DCF Intrinsic" value={money(fairValue?.intrinsic_estimates?.dcf_value ?? fairValue?.estimates.dcf_fair_value)} subvalue="Cash-flow model, before analyst target" />
                  <MetricTile title="EPS Value" value={money(fairValue?.intrinsic_estimates?.earnings_power_value ?? fairValue?.estimates.earnings_power_value)} subvalue="EPS x fair PE" />
                  <MetricTile title="Forward PE" value={numberText(valuation.metrics.forward_pe)} subvalue="Lower can be cheaper" />
                  <MetricTile title="PEG" value={numberText(valuation.metrics.peg_ratio)} subvalue="Growth-adjusted PE" />
                </div>
                <div className="mt-5 rounded-md bg-subtle p-4 text-sm text-muted-foreground">
                  <div className="font-medium text-foreground">Assumptions</div>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <div>Growth: {pct(typeof fairValue?.assumptions.growth_rate_pct === "number" ? fairValue.assumptions.growth_rate_pct : null)}</div>
                    <div>Discount: {pct(typeof fairValue?.assumptions.discount_rate_pct === "number" ? fairValue.assumptions.discount_rate_pct : null)}</div>
                    <div>Terminal: {pct(typeof fairValue?.assumptions.terminal_growth_pct === "number" ? fairValue.assumptions.terminal_growth_pct : null)}</div>
                    <div>Fair PE: {numberText(typeof fairValue?.assumptions.fair_pe_multiple === "number" ? fairValue.assumptions.fair_pe_multiple : null)}</div>
                    <div>Enterprise value: {compact(typeof dcfBreakdown?.enterprise_value === "number" ? dcfBreakdown.enterprise_value : null)}</div>
                    <div>Liquid assets: {compact(typeof dcfBreakdown?.total_liquid_assets === "number" ? dcfBreakdown.total_liquid_assets : null)}</div>
                    <div>Bridge debt: {compact(typeof dcfBreakdown?.debt_included_in_bridge === "number" ? dcfBreakdown.debt_included_in_bridge : null)}</div>
                    <div>Equity value: {compact(typeof dcfBreakdown?.equity_value === "number" ? dcfBreakdown.equity_value : null)}</div>
                    <div>Shares: {compact(typeof dcfBreakdown?.total_diluted_shares === "number" ? dcfBreakdown.total_diluted_shares : null)}</div>
                    <div>Share source: {String(dcfBreakdown?.share_count_source ?? "Unavailable")}</div>
                  </div>
                  {Array.isArray(dcfBreakdown?.warnings) && dcfBreakdown.warnings.length ? (
                    <div className="mt-3 text-amber-700">{dcfBreakdown.warnings.join(" ")}</div>
                  ) : null}
                </div>
              </>
            ) : (
              <div className="mt-5">
                <EmptySection message="Valuation data is unavailable from the free provider for this ticker." />
              </div>
            )}
          </div>
        </section>

        <section id="earnings" className="rounded-lg border border-border bg-card p-6 scroll-mt-20">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-lg font-semibold">Earnings</div>
              <p className="mt-1 text-sm text-muted-foreground">EPS, revenue, and earnings dates are shown only when available from the free data source.</p>
            </div>
          </div>
          {earnings ? (
            <>
              <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <MetricTile title="Reported EPS" value={numberText(earnings.reported_eps)} subvalue={`YoY ${pct(earnings.eps_change_pct)}`} />
                <MetricTile title="Estimated EPS" value={numberText(earnings.estimated_eps)} subvalue="Forward EPS when available" />
                <MetricTile title="Reported Revenue" value={compact(earnings.reported_revenue)} subvalue={`YoY ${pct(earnings.revenue_change_pct)}`} />
                <MetricTile title="Surprise" value={<Badge tone={earnings.surprise?.status === "beat" ? "good" : earnings.surprise?.status === "missed" ? "bad" : "neutral"}>{earnings.surprise?.status ?? "unavailable"}</Badge>} subvalue={earnings.surprise?.note ?? "Provider did not return surprise data."} />
              </div>
              <div className="mt-4 rounded-md bg-subtle p-4 text-sm text-muted-foreground">
                Recent earnings date: <span className="font-medium text-foreground">{dateText(earnings.recent_earnings_date)}</span>. Next expected earnings date: <span className="font-medium text-foreground">{dateText(earnings.next_earnings_date)}</span>.
              </div>
            </>
          ) : (
            <div className="mt-5">
              <EmptySection message="Earnings details are unavailable from the free provider for this ticker. The rest of the dashboard remains available." />
            </div>
          )}
        </section>

        <section id="quality" className="grid gap-4 lg:grid-cols-3 scroll-mt-20">
          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div className="text-lg font-semibold">Balance sheet</div>
              {balanceSheet ? <Badge tone={scoreTone(balanceSheet.score)}>{balanceSheet.score}/100</Badge> : null}
            </div>
            {balanceSheet ? (
              <>
                <div className="mt-5 grid gap-3">
                  <MetricTile title="Cash-Only Net Debt" value={compact(typeof balanceSheet.metrics.strict_cash_net_debt === "number" ? balanceSheet.metrics.strict_cash_net_debt : null)} subvalue="Interest-bearing debt minus cash" />
                  <MetricTile title="Liquidity Net Cash" value={compact(typeof balanceSheet.metrics.liquidity_adjusted_net_cash === "number" ? balanceSheet.metrics.liquidity_adjusted_net_cash : null)} subvalue="Cash plus eligible securities minus debt" />
                  <MetricTile title="Liquid Assets" value={compact(typeof balanceSheet.metrics.total_liquid_assets === "number" ? balanceSheet.metrics.total_liquid_assets : null)} subvalue={`Period ${balanceSheet.period_end ?? "unavailable"}`} />
                  <MetricTile title="Debt / Liquid Assets" value={numberText(balanceSheet.metrics.debt_to_liquid_assets)} subvalue="Leases shown separately when available" />
                  <MetricTile title="Current Ratio" value={numberText(balanceSheet.metrics.current_ratio)} subvalue="Same reporting period" />
                  <MetricTile title="Lease Liabilities" value={compact(typeof balanceSheet.metrics.lease_liabilities === "number" ? balanceSheet.metrics.lease_liabilities : null)} subvalue={balanceSheet.source ?? "Source unavailable"} />
                </div>
                <div className="mt-4 space-y-2 text-sm text-muted-foreground">
                  {[...(balanceSheet.strengths.length ? balanceSheet.strengths : balanceSheet.concerns.length ? balanceSheet.concerns : ["Balance sheet data is limited."]), ...(balanceSheet.warnings ?? [])].map((item, index) => (
                    <div key={index}>{item}</div>
                  ))}
                </div>
              </>
            ) : (
              <div className="mt-5">
                <EmptySection message="Balance sheet metrics are unavailable for this ticker." />
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div className="text-lg font-semibold">Dividend</div>
              {dividend ? <Badge tone={scoreTone(dividend.score)}>{dividend.score}/100</Badge> : null}
            </div>
            {dividend ? (
              <>
                <div className="mt-3 text-xl font-semibold">{dividend.label}</div>
                <div className="mt-5 grid gap-3">
                  <MetricTile title="Yield" value={pct(typeof dividend.metrics.dividend_yield_pct === "number" ? dividend.metrics.dividend_yield_pct : typeof dividend.metrics.dividend_yield === "number" ? dividend.metrics.dividend_yield * 100 : null)} subvalue="Annual dividend yield" />
                  <MetricTile title="Payout Ratio" value={pct(typeof dividend.metrics.payout_ratio === "number" ? dividend.metrics.payout_ratio * 100 : null)} subvalue="Lower is safer" />
                </div>
              </>
            ) : (
              <div className="mt-5">
                <EmptySection message="Dividend data is unavailable or not meaningful for this ticker." />
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-3">
              <div className="text-lg font-semibold">Analyst view</div>
              {analyst ? <Badge tone={scoreTone(analyst.score)}>{analyst.score}/100</Badge> : null}
            </div>
            {analyst ? (
              <>
                <div className="mt-3 text-xl font-semibold capitalize">{analyst.recommendation ?? "Unavailable"}</div>
                <div className="mt-5 grid gap-3">
                  <MetricTile title="Target Price" value={money(analyst.metrics.target_mean_price)} subvalue="Mean Wall Street target" />
                  <MetricTile title="Target Upside" value={pct(analyst.metrics.target_upside_pct)} subvalue="Versus current price" />
                </div>
              </>
            ) : (
              <div className="mt-5">
                <EmptySection message="Analyst target data is unavailable from the free provider." />
              </div>
            )}
          </div>
        </section>

        <section id="signals" className="rounded-lg border border-border bg-card p-6 scroll-mt-20">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold">Relevant news</div>
              <p className="mt-1 text-sm text-muted-foreground">Headlines are informational in Phase 1 and do not contribute to the overall score.</p>
            </div>
            <Badge tone="neutral">{newsItems.length} items</Badge>
          </div>
          <div className="mt-5 space-y-3">
            {newsItems.length ? (
              newsItems.slice(0, 5).map((item, index) => (
                <div key={index} className="rounded-lg border border-border bg-subtle p-3 text-sm">
                  <div className="font-medium leading-snug">{item.headline}</div>
                </div>
              ))
            ) : (
              <EmptySection message="No sufficiently relevant recent headlines found." />
            )}
          </div>
        </section>
        <section id="ai-assistant" className="rounded-lg border border-border bg-card p-6 scroll-mt-20">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-lg font-semibold">AI Research Assistant</div>
                <Badge tone="neutral">Future ChatGPT App</Badge>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                A ChatGPT App is under development. It will use this dashboard's structured market and financial data to explain company performance, valuation, risks, trends, earnings, and research scenarios inside ChatGPT.
              </p>
            </div>
            <Link href="/chatgpt-app" className="rounded-md border border-border bg-subtle px-3 py-2 text-sm font-medium text-foreground hover:bg-surface">
              View ChatGPT App
            </Link>
          </div>
        </section>
        <section id="previous-predictions" className="rounded-lg border border-border bg-card p-6 scroll-mt-20">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-lg font-semibold">Previous prediction tools</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Preserved outputs from the original app: traditional stock-price ML, News API sentiment, and the financial-statement prediction model. Reddit is intentionally excluded while it is down.
              </p>
            </div>
            <Badge tone="neutral">{legacyLoading ? "Loading original signals" : "Original signals"}</Badge>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-border bg-subtle p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="font-semibold">Traditional ML stock-price model</div>
                {previousPrediction ? <Badge tone={directionTone(previousPrediction.direction)}>{previousPrediction.direction}</Badge> : <Badge tone="warn">Unavailable</Badge>}
              </div>
              {previousPrediction ? (
                <div className="mt-4 grid gap-3">
                  <MetricTile title="Predicted Price" value={money(previousPrediction.predicted_price)} subvalue="From the preserved /predict model" />
                  <MetricTile title="Predicted Move" value={pct(previousPrediction.predicted_change_pct)} subvalue={confidenceText(previousPrediction.confidence)} />
                  <MetricTile title="Price Used" value={money((previousPrediction as PredictionData & { current_price?: number }).current_price ?? null)} subvalue={previousPrediction.current_price_as_of ? `Quote as of ${dateTimeText(previousPrediction.current_price_as_of)}` : sourceLabel(previousPrediction.current_price_source)} />
                  <MetricTile title="Model Input Through" value={dateText(previousPrediction.model_input_end_date)} subvalue={previousPrediction.model_input_start_date ? `Training window starts ${dateText(previousPrediction.model_input_start_date)}` : "Prediction input timestamp"} />
                  <MetricTile title="Models" value={predictionModelNames(previousPrediction.model_info)} subvalue={predictionModelRoleText(previousPrediction.model_info)} />
                </div>
              ) : (
                <SectionNotice
                  title="Stock-price ML unavailable"
                  message={predictionWarning ?? "This model needs live price history. If Yahoo/yfinance cannot fetch prices, this previous prediction cannot render."}
                />
              )}
            </div>

            <div className="rounded-lg border border-border bg-subtle p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="font-semibold">News API sentiment model</div>
                <Badge tone={previousNewsCounts.total ? "neutral" : "warn"}>{previousNewsCounts.total} headlines</Badge>
              </div>
              <div className="mt-4 space-y-3">
                <SentimentBar label="Positive" value={previousNewsCounts.positive} total={previousNewsCounts.total} />
                <SentimentBar label="Neutral" value={previousNewsCounts.neutral} total={previousNewsCounts.total} />
                <SentimentBar label="Negative" value={previousNewsCounts.negative} total={previousNewsCounts.total} />
              </div>
              <div className="mt-4 space-y-2">
                {previousNewsItems.length ? (
                  previousNewsItems.slice(0, 3).map((item, index) => (
                    <div key={index} className="rounded-md border border-border bg-card p-3 text-sm">
                      <div className="font-medium leading-snug">{item.headline}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{item.sentiment}</div>
                    </div>
                  ))
                ) : (
                  <SectionNotice
                    title="News sentiment unavailable"
                    message={newsWarning ?? "The preserved /api/news signal returned no headlines for this ticker."}
                  />
                )}
              </div>
            </div>

            <div className="rounded-lg border border-border bg-subtle p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="font-semibold">Financial-statement prediction</div>
                {previousFinancialDirection ? (
                  <Badge tone={directionTone(previousFinancialDirection)}>{previousFinancialDirection}</Badge>
                ) : (
                  <Badge tone="warn">Unavailable</Badge>
                )}
              </div>
              {previousFinancialDirection ? (
                <div className="mt-4 grid gap-3">
                  <MetricTile title="Direction" value={previousFinancialDirection} subvalue="From the preserved /api/financials model" />
                  <MetricTile title="Confidence" value={confidenceText(previousFinancialConfidence)} subvalue="Financial statement model" />
                  <MetricTile title="Data Source" value={legacyFinancial ? "/api/financials" : analysis?.financials?.source ?? "Financial statements"} subvalue="Uses available statement data" />
                </div>
              ) : (
                <SectionNotice
                  title="Financial prediction unavailable"
                  message={financialWarning ?? "The preserved /api/financials signal did not return a model output for this ticker."}
                />
              )}
            </div>
          </div>
        </section>

        <section id="sources" className="rounded-lg border border-border bg-card p-5 text-sm text-muted-foreground scroll-mt-20">
          <div className="text-lg font-semibold text-foreground">Data sources and limitations</div>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            <div>Sources loaded: {analysis?.data_quality?.sources?.join(", ") || "none yet"}</div>
            <div>Cache: {analysis?.data_quality?.cache?.status ?? "not loaded"}{typeof analysis?.data_quality?.cache?.ttl_seconds === "number" ? ` (${Math.round((analysis.data_quality.cache.ttl_seconds ?? 0) / 60)} min left)` : ""}</div>
            <div>Reddit: {analysis?.reddit?.disabled ? analysis.reddit.reason : "not requested"}</div>
            <div>Price quote: {priceSource} ({priceSession}) as of {priceAsOf}</div>
            <div>Cost: no paid data, AI, hosting, or database services were added for Phase 1.</div>
          </div>
          <div className="mt-3">{priceDelayNote}</div>
          <div className="mt-2">{analysis?.summary.disclaimer ?? "This platform is for educational and research purposes and does not provide financial advice."}</div>
        </section>
      </main>
    </div>
  );
}
















