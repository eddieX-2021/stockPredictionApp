"use client";

import { useEffect, useMemo, useState } from "react";
import Autosuggest from "react-autosuggest";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useDebounce } from "use-debounce";

interface Stock {
  symbol: string;
  name: string;
}

const POPULAR_SYMBOLS = [
  "AAPL","MSFT","GOOGL","GOOG","AMZN","TSLA","META","NVDA","NFLX","INTC",
  "AMD","CRM","ORCL","IBM","ADBE","CSCO",
  "JPM","BAC","WFC","C","GS","MS","AXP",
  "WMT","TGT","COST","HD","LOW","NKE","SBUX","MCD",
  "UNH","JNJ","PFE","MRK","ABBV","LLY","BMY",
  "PG","KO","PEP","PM","MO",
  "XOM","CVX","COP","SLB","EOG",
  "UPS","FDX","CAT","DE","BA","LMT","GE",
  "VZ","T","TMUS",
  "SPY","QQQ","DIA","VTI","VOO","ARKK","XLK","XLF","XLE","IWM",
];

function classNames(...xs: Array<string | false | undefined | null>) {
  return xs.filter(Boolean).join(" ");
}

export default function Home() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [stockData, setStockData] = useState<Stock[]>([]);
  const [debouncedQuery] = useDebounce(query, 250);
  const router = useRouter();

  useEffect(() => {
    const fetchStockData = async () => {
      try {
        const res = await fetch(
          `/api/finnhub-stocks?query=${encodeURIComponent(debouncedQuery)}`
        );
        const data = await res.json();
        setStockData(Array.isArray(data) ? data : []);
      } catch {
        setStockData([]);
      }
    };

    if (debouncedQuery.length > 1) fetchStockData();
    else setStockData([]);
  }, [debouncedQuery]);

  const getSuggestions = (value: string) => {
    const inputValue = value.trim().toLowerCase();
    if (inputValue.length === 0) return [];

    const filtered = stockData.reduce(
      (acc, s) => {
        if (s.symbol.toLowerCase().startsWith(inputValue)) acc.symbol.push(s);
        else if (s.name.toLowerCase().startsWith(inputValue)) acc.name.push(s);
        return acc;
      },
      { symbol: [] as Stock[], name: [] as Stock[] }
    );

    const sortStocks = (xs: Stock[]) =>
      xs.sort((a, b) => {
        const ap = POPULAR_SYMBOLS.includes(a.symbol);
        const bp = POPULAR_SYMBOLS.includes(b.symbol);
        if (ap && !bp) return -1;
        if (!ap && bp) return 1;
        return a.symbol.localeCompare(b.symbol);
      });

    return [...sortStocks(filtered.symbol), ...sortStocks(filtered.name)].slice(0, 10);
  };

  useEffect(() => {
    setSuggestions(getSuggestions(query));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, stockData]);

  const onSuggestionsFetchRequested = ({ value }: { value: string }) => {
    setSuggestions(getSuggestions(value));
  };

  const onSuggestionsClearRequested = () => setSuggestions([]);

  const onChange = (_: React.FormEvent<HTMLElement>, { newValue }: { newValue: string }) => {
    setQuery(newValue);
  };

  const onSuggestionSelected = (_: React.FormEvent<HTMLElement>, { suggestion }: { suggestion: Stock }) => {
    setQuery(suggestion.symbol);
    router.push(`/${suggestion.symbol}`);
  };

  const onKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && query) {
      const matched = stockData.find((s) => s.symbol.toUpperCase() === query.toUpperCase());
      if (matched) router.push(`/${matched.symbol}`);
    }
  };

  const renderSuggestion = (s: Stock) => (
    <div className="px-3 py-2.5 hover:bg-black/5 cursor-pointer">
      <div className="flex items-center justify-between">
        <span className="font-semibold tracking-wide">{s.symbol}</span>
        <span className="text-xs text-muted-foreground">Ticker</span>
      </div>
      <div className="text-sm text-muted-foreground line-clamp-1">{s.name}</div>
    </div>
  );

  const inputProps = useMemo(
    () => ({
      placeholder: "Search a ticker (AAPL) or company name (Apple)…",
      value: query,
      onChange,
      onKeyPress,
      className:
        "w-full rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-base text-white placeholder:text-white/60 outline-none backdrop-blur focus:ring-2 focus:ring-white/40",
    }),
    [query]
  );

  return (
    <main className="min-h-screen">
      {/* HERO */}
      <section className="relative overflow-hidden">
        {/* Background image (replace /public/hero.jpg) */}
        <div className="absolute inset-0 -z-10">
          <Image
            src="/money.jpg"
            alt="Background"
            fill
            priority
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/55 to-bg" />
        </div>

        <div className="mx-auto max-w-6xl px-6 pt-20 pb-16">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-sm text-white/85">
              <span className="h-2 w-2 rounded-full bg-emerald-400" />
              Market signals • News + Reddit • Financials
            </div>

            <h1 className="mt-5 text-4xl font-semibold tracking-tight text-white sm:text-5xl">
              Your Personal Revenue Driver
              <span className="block text-white/80">Fast to search. Easy to read.</span>
            </h1>

            <p className="mt-4 text-base leading-relaxed text-white/80">
              We estimate next-step price movement using historical price patterns (Yahoo),
              sentiment from financial news + Reddit, and fundamentals from financial reports.
              This is a decision-support tool—always validate with your own research.
            </p>

            {/* Search */}
            <div className="mt-8">
              <div className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur">
                <div className="text-sm font-medium text-white/80 mb-2">
                  Search a stock to generate the dashboard
                </div>

                <Autosuggest
                  suggestions={suggestions}
                  onSuggestionsFetchRequested={onSuggestionsFetchRequested}
                  onSuggestionsClearRequested={onSuggestionsClearRequested}
                  getSuggestionValue={(s) => s.symbol}
                  renderSuggestion={renderSuggestion}
                  inputProps={inputProps}
                  onSuggestionSelected={onSuggestionSelected}
                  theme={{
                    container: "relative",
                    suggestionsContainer:
                      "absolute z-10 mt-2 w-full overflow-hidden rounded-xl border border-white/10 bg-white shadow-2xl",
                    suggestionHighlighted: "bg-black/5",
                  }}
                />

                <div className="mt-3 text-xs text-white/70">
                  Tip: try <span className="font-semibold">AAPL</span>,{" "}
                  <span className="font-semibold">NVDA</span>,{" "}
                  <span className="font-semibold">TSLA</span>,{" "}
                  <span className="font-semibold">SPY</span>
                </div>
              </div>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-white/85">
                <div className="text-sm font-semibold">Historical signals</div>
                <div className="mt-1 text-sm text-white/70">
                  Price/volume patterns from Yahoo market history.
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-white/85">
                <div className="text-sm font-semibold">News + Reddit sentiment</div>
                <div className="mt-1 text-sm text-white/70">
                  Headlines + posts classified to measure market tone.
                </div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-white/85">
                <div className="text-sm font-semibold">Fundamentals</div>
                <div className="mt-1 text-sm text-white/70">
                  Financial reports used to weight the prediction context.
                </div>
              </div>
            </div>
          </div>

          {/* Scroll hint */}
          <div className="mt-16 flex items-center gap-2 text-white/70">
            <div className="h-10 w-6 rounded-full border border-white/20 flex items-start justify-center p-1">
              <div className="h-2 w-2 rounded-full bg-white/70 animate-bounce" />
            </div>
            <span className="text-sm">Scroll to learn how it works</span>
          </div>
        </div>
      </section>

      {/* DESCRIPTION (scroll section) */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-10 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">
              How the prediction is made
            </h2>
            <p className="mt-3 text-muted-foreground leading-relaxed">
              We combine three signal groups:
              <span className="font-medium text-foreground"> historical price behavior</span>{" "}
              (Yahoo), <span className="font-medium text-foreground">market narrative</span>{" "}
              (news + Reddit sentiment), and{" "}
              <span className="font-medium text-foreground">company fundamentals</span>{" "}
              (financial reports). The dashboard prioritizes the most useful numbers so you can
              decide quickly.
            </p>

            <ol className="mt-6 space-y-3">
              <li className="flex gap-3">
                <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black text-white text-xs">
                  1
                </span>
                <div>
                  <div className="font-medium">Pull historical prices</div>
                  <div className="text-sm text-muted-foreground">
                    Past price/volume gives trend + volatility context.
                  </div>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black text-white text-xs">
                  2
                </span>
                <div>
                  <div className="font-medium">Score sentiment</div>
                  <div className="text-sm text-muted-foreground">
                    News + Reddit sentiment estimates short-term market tone.
                  </div>
                </div>
              </li>
              <li className="flex gap-3">
                <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black text-white text-xs">
                  3
                </span>
                <div>
                  <div className="font-medium">Blend with fundamentals</div>
                  <div className="text-sm text-muted-foreground">
                    Financials help avoid “hype-only” predictions.
                  </div>
                </div>
              </li>
            </ol>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-border bg-card overflow-hidden">
              <div className="relative aspect-[4/3]">
                <Image
                  src="/eg1.jpg"
                  alt="Placeholder 1"
                  fill
                  className="object-cover"
                />
              </div>
              <div className="p-4">
                <div className="font-medium">Dashboard snapshot</div>
                <div className="text-sm text-muted-foreground">
                  Replace this with your own screenshot later.
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card overflow-hidden">
              <div className="relative aspect-[4/3]">
                <Image
                  src="/eg2.jpg"
                  alt="Placeholder 2"
                  fill
                  className="object-cover"
                />
              </div>
              <div className="p-4">
                <div className="font-medium">Signals overview</div>
                <div className="text-sm text-muted-foreground">
                  Another placeholder for your design / chart.
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 rounded-2xl border border-border bg-card p-6">
          <div className="font-medium">Disclaimer</div>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            Predictions can be wrong. This app is for educational and informational purposes,
            not financial advice.
          </p>
        </div>
      </section>
    </main>
  );
}
