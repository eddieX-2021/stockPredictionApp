// /app/api/finnhub-stocks/route.ts
import { NextResponse } from "next/server";

type FinnhubSymbolRaw = {
  symbol: string;
  description?: string;
  displaySymbol?: string;
  currency?: string;
  type?: string;
};

/** Narrowing guard for the raw Finnhub symbol entry */
function isFinnhubSymbolRaw(item: unknown): item is FinnhubSymbolRaw {
  if (typeof item !== "object" || item === null) return false;
  const maybe = item as Record<string, unknown>;
  if (typeof maybe.symbol !== "string") return false;
  if (
    typeof maybe.description !== "undefined" &&
    typeof maybe.description !== "string"
  )
    return false;
  return true;
}

export async function GET(request: Request) {
  try {
    const apiKey = process.env.FINNHUB_API_KEY;
    if (!apiKey) {
      console.error("Missing FINNHUB_API_KEY");
      return NextResponse.json(
        { error: "Finnhub API key is missing" },
        { status: 500 }
      );
    }

    // allow optional exchange query param, default to US
    const url = new URL(request.url);
    const exchange = url.searchParams.get("exchange") ?? "US";

    const resp = await fetch(
      `https://finnhub.io/api/v1/stock/symbol?exchange=${encodeURIComponent(
        exchange
      )}&token=${encodeURIComponent(apiKey)}`
    );

    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      console.error(
        "Finnhub responded with non-OK status:",
        resp.status,
        text
      );
      return NextResponse.json(
        { error: "Failed to fetch data from Finnhub" },
        { status: resp.status }
      );
    }

    const raw = await resp.json();

    if (!Array.isArray(raw)) {
      console.error("Unexpected Finnhub response shape:", raw);
      return NextResponse.json(
        { error: "Unexpected response format from Finnhub" },
        { status: 502 }
      );
    }

    const stocks = raw
      .filter(isFinnhubSymbolRaw)
      .map((item) => ({
        symbol: item.symbol,
        name:
          item.description && item.description.trim() !== ""
            ? item.description
            : item.symbol,
      }));

    return NextResponse.json(stocks, {
      headers: {
        // optional caching for CDN / ISR consumers
        "Cache-Control": "s-maxage=300, stale-while-revalidate=60",
      },
    });
  } catch (error) {
    console.error("Error fetching Finnhub data:", error);
    return NextResponse.json(
      { error: "Failed to fetch stock data" },
      { status: 500 }
    );
  }
}
