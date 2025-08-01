import { NextResponse } from "next/server";

interface FinnhubSymbol {
  symbol: string;
  description?: string;
  displaySymbol?: string;
  // (you can add other properties here if you need them)
}

export async function GET() {
  try {
    const apiKey = process.env.FINNHUB_API_KEY;
    if (!apiKey) {
      throw new Error("Finnhub API key is missing");
    }

    const res = await fetch(
      `https://finnhub.io/api/v1/stock/symbol?exchange=US&token=${apiKey}`
    );
    if (!res.ok) {
      throw new Error("Failed to fetch data from Finnhub");
    }

    // Tell TypeScript exactly what shape to expect
    const data: FinnhubSymbol[] = await res.json();

    const stocks = data.map((item) => ({
      symbol: item.symbol,
      name: item.description || item.symbol,
    }));

    return NextResponse.json(stocks);
  } catch (err) {
    console.error("Error fetching Finnhub data:", err);
    return NextResponse.json(
      { error: "Failed to fetch stock data" },
      { status: 500 }
    );
  }
}