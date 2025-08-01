"use client";

import { useState, useEffect } from "react";
import Autosuggest from "react-autosuggest";
import { useRouter } from "next/navigation";
import { useDebounce } from "use-debounce";

interface Stock {
  symbol: string;
  name: string;
}

// List of popular stock symbols to prioritize
const POPULAR_SYMBOLS = [
  // Tech
  "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "NFLX", "INTC",
  "AMD", "CRM", "ORCL", "IBM", "ADBE", "CSCO",
  // Financials
  "JPM", "BAC", "WFC", "C", "GS", "MS", "AXP",
  // Consumer Goods / Retail
  "WMT", "TGT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD",
  // Healthcare
  "UNH", "JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY",
  // Consumer Staples
  "PG", "KO", "PEP", "PM", "MO",
  // Energy
  "XOM", "CVX", "COP", "SLB", "EOG",
  // Industrials / Other
  "UPS", "FDX", "CAT", "DE", "BA", "LMT", "GE",
  // Telecom & Others
  "VZ", "T", "TMUS",
  // ETF
  "SPY", "QQQ", "DIA", "VTI", "VOO", "ARKK", "XLK", "XLF", "XLE", "IWM",
  // Space & Aerospace Stocks
  "SPCE", "RKLB", "MAXR", "ASTR", "LHX", "NOC", "BA", "LMT", "IRDM", "SIRI", "PL",
];

export default function Home() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const [stockData, setStockData] = useState<Stock[]>([]);
  const [debouncedQuery] = useDebounce(query, 300);
  const router = useRouter();

  // Fetch stock data from Finnhub API
  useEffect(() => {
    const fetchStockData = async () => {
      try {
        const response = await fetch(`/api/finnhub-stocks?query=${encodeURIComponent(debouncedQuery)}`);
        const data = await response.json();
        
        if (Array.isArray(data)) {
          setStockData(data);
        } else {
          setStockData([]);
        }
      } catch (error) {
        console.error("Error fetching stock data:", error);
        setStockData([]);
      }
    };

    if (debouncedQuery.length > 1) {
      fetchStockData();
    } else {
      setStockData([]);
    }
  }, [debouncedQuery]);

  // Get suggestions based on user input (symbol starts with input first, then name starts with input)
  const getSuggestions = (value: string) => {
    const inputValue = value.trim().toLowerCase();
    if (inputValue.length === 0) return [];

    // Filter stocks by symbol or name starting with input
    const filteredStocks = stockData.reduce(
      (acc, stock) => {
        if (stock.symbol.toLowerCase().startsWith(inputValue)) {
          acc.symbolMatches.push(stock);
        } else if (stock.name.toLowerCase().startsWith(inputValue)) {
          acc.nameMatches.push(stock);
        }
        return acc;
      },
      { symbolMatches: [], nameMatches: [] } as {
        symbolMatches: Stock[];
        nameMatches: Stock[];
      }
    );

    // Sort each group: prioritize popular symbols, then alphabetically by symbol
    const sortStocks = (stocks: Stock[]) =>
      stocks.sort((a, b) => {
        const aIsPopular = POPULAR_SYMBOLS.includes(a.symbol);
        const bIsPopular = POPULAR_SYMBOLS.includes(b.symbol);
        if (aIsPopular && !bIsPopular) return -1;
        if (!aIsPopular && bIsPopular) return 1;
        return a.symbol.localeCompare(b.symbol);
      });

    // Combine symbol matches (first) and name matches (second), limit to 10
    return [
      ...sortStocks(filteredStocks.symbolMatches),
      ...sortStocks(filteredStocks.nameMatches),
    ].slice(0, 10);
  };

  // Update suggestions when query changes
  useEffect(() => {
    setSuggestions(getSuggestions(query));
  }, [query, stockData]);

  // Autosuggest event handlers
  const onSuggestionsFetchRequested = ({ value }: { value: string }) => {
    setSuggestions(getSuggestions(value));
  };

  const onSuggestionsClearRequested = () => {
    setSuggestions([]);
  };

  const onChange = (
    event: React.FormEvent<HTMLElement>,
    { newValue }: { newValue: string }
  ) => {
    setQuery(newValue);
  };

  const onSuggestionSelected = (
    event: React.FormEvent<HTMLElement>,
    { suggestion }: { suggestion: Stock }
  ) => {
    setQuery(suggestion.symbol);
    router.push(`/${suggestion.symbol}`);
  };

  // Handle Enter key press
  const onKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && query) {
      const matchedStock = stockData.find(
        (stock) => stock.symbol.toUpperCase() === query.toUpperCase()
      );
      if (matchedStock) {
        router.push(`/${matchedStock.symbol}`);
      }
    }
  };

  // Render suggestion item (symbol bold, name lighter with margin)
  const renderSuggestion = (suggestion: Stock) => (
    <div className="p-2 hover:bg-gray-100 cursor-pointer">
      <span className="font-medium">{suggestion.symbol}</span>
      <span className="ml-2 text-gray-600 text-sm">{suggestion.name}</span>
    </div>
  );

  // Autosuggest input props
  const inputProps = {
    placeholder: "Search for a stock symbol or company name...",
    value: query,
    onChange,
    onKeyPress,
    className:
      "w-full p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500",
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-100">
      <h1 className="text-4xl font-bold text-center mb-8">Best Gambling Website NA</h1>
      <div className="w-full max-w-md">
        <Autosuggest
          suggestions={suggestions}
          onSuggestionsFetchRequested={onSuggestionsFetchRequested}
          onSuggestionsClearRequested={onSuggestionsClearRequested}
          getSuggestionValue={(suggestion: Stock) => suggestion.symbol}
          renderSuggestion={renderSuggestion}
          inputProps={inputProps}
          theme={{
            container: "relative",
            suggestionsContainer:
              "absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto",
            suggestionHighlighted: "bg-gray-100",
          }}
        />
      </div>
    </div>
  );
}