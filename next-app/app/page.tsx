"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useCombobox, type UseComboboxStateChange } from "downshift";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useDebounce } from "use-debounce";

interface Stock {
  symbol: string;
  name: string;
}

const POPULAR_SYMBOLS: ReadonlyArray<string> = [
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

function safeUpper(s: string) {
  return s.trim().toUpperCase();
}

export default function Home() {
  const [query, setQuery] = useState<string>("");
  const [stockData, setStockData] = useState<Stock[]>([]);
  const [debouncedQuery] = useDebounce(query, 250);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    async function fetchStockData() {
      try {
        const res = await fetch(
          `/api/finnhub-stocks?query=${encodeURIComponent(debouncedQuery)}`
        );

        const data: unknown = await res.json();

        if (cancelled) return;

        // runtime guard (no `any`)
        const next: Stock[] = Array.isArray(data)
          ? data.filter((x): x is Stock => {
              if (typeof x !== "object" || x === null) return false;
              const rec = x as Record<string, unknown>;
              return typeof rec.symbol === "string" && typeof rec.name === "string";
            })
          : [];

        setStockData(next);
      } catch {
        if (!cancelled) setStockData([]);
      }
    }

    if (debouncedQuery.length > 1) fetchStockData();
    else setStockData([]);

    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  const suggestions = useMemo<Stock[]>(() => {
    const inputValue = query.trim().toLowerCase();
    if (inputValue.length === 0) return [];

    const symbolMatches: Stock[] = [];
    const nameMatches: Stock[] = [];

    for (const s of stockData) {
      if (s.symbol.toLowerCase().startsWith(inputValue)) symbolMatches.push(s);
      else if (s.name.toLowerCase().startsWith(inputValue)) nameMatches.push(s);
    }

    const sortStocks = (xs: Stock[]) =>
      [...xs].sort((a, b) => {
        const ap = POPULAR_SYMBOLS.includes(a.symbol);
        const bp = POPULAR_SYMBOLS.includes(b.symbol);
        if (ap && !bp) return -1;
        if (!ap && bp) return 1;
        return a.symbol.localeCompare(b.symbol);
      });

    return [...sortStocks(symbolMatches), ...sortStocks(nameMatches)].slice(0, 10);
  }, [query, stockData]);

  const navigateToSymbol = useCallback(
    (symbol: string) => {
      const s = safeUpper(symbol);
      if (!s) return;
      router.push(`/${s}`);
    },
    [router]
  );

  const onInputValueChange = useCallback(
    (changes: UseComboboxStateChange<Stock>) => {
      setQuery(changes.inputValue ?? "");
    },
    []
  );

  const onSelectedItemChange = useCallback(
    (changes: UseComboboxStateChange<Stock>) => {
      if (changes.selectedItem) {
        navigateToSymbol(changes.selectedItem.symbol);
      }
    },
    [navigateToSymbol]
  );

  const {
    isOpen,
    getMenuProps,
    getInputProps,
    highlightedIndex,
    getItemProps,
  } = useCombobox<Stock>({
    items: suggestions,
    itemToString: (item) => (item ? item.symbol : ""),
    onInputValueChange,
    onSelectedItemChange,
  });

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key !== "Enter") return;

      const q = safeUpper(query);
      if (!q) return;

      // If user typed AAPL and it exists in fetched items, normalize to that symbol
      const matched = stockData.find((s) => safeUpper(s.symbol) === q);
      if (matched) navigateToSymbol(matched.symbol);
      else navigateToSymbol(q); // allow direct navigation even if not in suggestions
    },
    [query, stockData, navigateToSymbol]
  );

  return (
    <main className="min-h-screen">
      {/* HERO */}
      <section className="relative overflow-hidden">
        {/* Background image */}
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
                <div className="mb-2 text-sm font-medium text-white/80">
                  Search a stock to generate the dashboard
                </div>

                <div className="relative">
                  <input
                    {...getInputProps({
                      onKeyDown: handleKeyDown,
                      placeholder: "Search a ticker (AAPL) or company name (Apple)…",
                      className:
                        "w-full rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-base text-white placeholder:text-white/60 outline-none backdrop-blur focus:ring-2 focus:ring-white/40",
                    })}
                  />

                  <ul
                    {...getMenuProps()}
                    className={`absolute z-10 mt-2 w-full overflow-hidden rounded-xl border border-white/10 bg-white shadow-2xl ${
                      isOpen && suggestions.length > 0 ? "" : "hidden"
                    }`}
                  >
                    {isOpen &&
                      suggestions.map((item, index) => (
                        <li
                          key={`${item.symbol}-${index}`}
                          {...getItemProps({ item, index })}
                          className={`cursor-pointer px-3 py-2.5 ${
                            highlightedIndex === index ? "bg-black/5" : ""
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold tracking-wide">
                              {item.symbol}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              Ticker
                            </span>
                          </div>
                          <div className="line-clamp-1 text-sm text-muted-foreground">
                            {item.name}
                          </div>
                        </li>
                      ))}
                  </ul>
                </div>

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
            <div className="flex h-10 w-6 items-start justify-center rounded-full border border-white/20 p-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-white/70" />
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
            <p className="mt-3 leading-relaxed text-muted-foreground">
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
                <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black text-xs text-white">
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
                <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black text-xs text-white">
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
                <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full bg-black text-xs text-white">
                  3
                </span>
                <div>
                  <div className="font-medium">Blend with fundamentals</div>
                  <div className="text-sm text-muted-foreground">
                    Financials help avoid &quot;hype-only&quot; predictions.
                  </div>
                </div>
              </li>
            </ol>
          </div>

          <div className="overflow-hidden rounded-2xl border border-border bg-card">
            {/* Image */}
            <div className="relative aspect-[16/10]">
              <Image
                src="/eg.png"
                alt="Dashboard snapshot"
                fill
                className="object-contain bg-white"
                priority
              />
            </div>

            {/* Caption */}
            <div className="p-5">
              <div className="text-lg font-semibold">Dashboard snapshot</div>
              <p className="mt-1 text-sm text-muted-foreground leading-relaxed">
                Example view of the prediction dashboard, highlighting key metrics,
                confidence, and sentiment breakdown.
              </p>
            </div>
          </div>

        </div>

        <div className="mt-12 rounded-2xl border border-border bg-card p-6">
          <div className="font-medium">Disclaimer</div>
          <p className="mt-2 leading-relaxed text-sm text-muted-foreground">
            Predictions can be wrong. This app is for educational and informational purposes,
            not financial advice.
          </p>
        </div>
      </section>
    </main>
  );
}
