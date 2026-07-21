import { NextResponse } from "next/server";

type StockSuggestion = {
  symbol: string;
  name: string;
};

interface FinnhubStock {
  symbol: string;
  description: string;
  type: string;
}

const FALLBACK_STOCKS: StockSuggestion[] = [
  { symbol: "AAPL", name: "Apple Inc." },
  { symbol: "MSFT", name: "Microsoft Corporation" },
  { symbol: "MU", name: "Micron Technology, Inc." },
  { symbol: "NVDA", name: "NVIDIA Corporation" },
  { symbol: "AMZN", name: "Amazon.com, Inc." },
  { symbol: "GOOGL", name: "Alphabet Inc." },
  { symbol: "META", name: "Meta Platforms, Inc." },
  { symbol: "TSLA", name: "Tesla, Inc." },
  { symbol: "AMD", name: "Advanced Micro Devices, Inc." },
  { symbol: "JPM", name: "JPMorgan Chase & Co." },
  { symbol: "SPY", name: "SPDR S&P 500 ETF Trust" },
  { symbol: "QQQ", name: "Invesco QQQ Trust" },
];

function fallbackSearch(query: string) {
  const q = query.trim().toUpperCase();
  if (q.length < 1) return [];

  return FALLBACK_STOCKS.filter(
    (stock) => stock.symbol.startsWith(q) || stock.name.toUpperCase().includes(q)
  ).slice(0, 10);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = (searchParams.get("query") || "").trim();

  if (query.length < 2) {
    return NextResponse.json([]);
  }

  const apiKey = process.env.FINNHUB_API_KEY;
  if (!apiKey) {
    return NextResponse.json(fallbackSearch(query));
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(
      `https://finnhub.io/api/v1/search?q=${encodeURIComponent(query)}&token=${apiKey}`,
      { signal: controller.signal }
    );

    if (!response.ok) {
      return NextResponse.json(fallbackSearch(query));
    }

    const data = (await response.json()) as { result?: FinnhubStock[] };
    const stocks = (data.result ?? [])
      .filter((item) => item.symbol && item.description && item.type === "Common Stock")
      .map((item) => ({
        symbol: item.symbol,
        name: item.description,
      }))
      .slice(0, 10);

    return NextResponse.json(stocks.length ? stocks : fallbackSearch(query));
  } catch (error) {
    console.error("Error fetching stock suggestions:", error);
    return NextResponse.json(fallbackSearch(query));
  } finally {
    clearTimeout(timeout);
  }
}
