import { NextResponse } from 'next/server';

// Define interface for Finnhub search result items
interface FinnhubStock {
  symbol: string;
  description: string;
  type: string;
  // Add other fields if needed (e.g., displaySymbol, primary)
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get('query') || '';

  // Require at least 2 characters to avoid excessive API calls
  if (query.length < 2) {
    return NextResponse.json([]);
  }

  try {
    const apiKey = process.env.FINNHUB_API_KEY;
    if (!apiKey) {
      throw new Error('Finnhub API key is not configured');
    }

    const response = await fetch(
      `https://finnhub.io/api/v1/search?q=${encodeURIComponent(query)}&token=${apiKey}`
    );
    const data = await response.json();

    if (!data.result) {
      return NextResponse.json([]);
    }

    const stocks = data.result
      .filter((item: FinnhubStock) => item.symbol && item.description && item.type === 'Common Stock')
      .map((item: FinnhubStock) => ({
        symbol: item.symbol,
        name: item.description,
      }))
      .slice(0, 10);

    return NextResponse.json(stocks);
  } catch (error) {
    console.error('Error fetching stock data:', error);
    return NextResponse.json([], { status: 500 });
  }
}