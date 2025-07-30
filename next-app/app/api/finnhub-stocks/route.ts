import { NextResponse } from "next/server";

export async function GET() {
  try {
    const apiKey = process.env.FINNHUB_API_KEY;
    if (!apiKey) {
      throw new Error("Finnhub API key is missing");
    }
    const response = await fetch(
      `https://finnhub.io/api/v1/stock/symbol?exchange=US&token=${apiKey}`
    );
    if (!response.ok) {
      throw new Error("Failed to fetch data from Finnhub");
    }
    const data = await response.json();
    const stocks = data.map((item: any) => ({
      symbol: item.symbol,
      name: item.description || item.symbol,
    }));
    return NextResponse.json(stocks);
  } catch (error) {
    console.error("Error fetching Finnhub data:", error);
    return NextResponse.json({ error: "Failed to fetch stock data" }, { status: 500 });
  }
}