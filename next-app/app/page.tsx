// "use client";

// import Image from "next/image";
// import { useState, useEffect } from "react";
// import Autosuggest from "react-autosuggest";

// interface Stock {
//   symbol: string;
//   name: string;
// }

// // List of popular stock symbols to prioritize
// const POPULAR_SYMBOLS = [
//   // Tech
//   "AAPL",    // Apple Inc.
//   "MSFT",    // Microsoft Corp.
//   "GOOGL",   // Alphabet Inc. (Google Class A)
//   "GOOG",    // Alphabet Inc. (Google Class C)
//   "AMZN",    // Amazon.com Inc.
//   "TSLA",    // Tesla Inc.
//   "META",    // Meta Platforms Inc.
//   "NVDA",    // NVIDIA Corp.
//   "NFLX",    // Netflix Inc.
//   "INTC",    // Intel Corp.
//   "AMD",     // Advanced Micro Devices Inc.
//   "CRM",     // Salesforce Inc.
//   "ORCL",    // Oracle Corp.
//   "IBM",     // International Business Machines Corp.
//   "ADBE",    // Adobe Inc.
//   "CSCO",    // Cisco Systems Inc.

//   // Financials
//   "JPM",     // JPMorgan Chase & Co.
//   "BAC",     // Bank of America Corp.
//   "WFC",     // Wells Fargo & Co.
//   "C",       // Citigroup Inc.
//   "GS",      // Goldman Sachs Group Inc.
//   "MS",      // Morgan Stanley
//   "AXP",     // American Express Co.

//   // Consumer Goods / Retail
//   "WMT",     // Walmart Inc.
//   "TGT",     // Target Corp.
//   "COST",    // Costco Wholesale Corp.
//   "HD",      // Home Depot Inc.
//   "LOW",     // Lowe’s Companies Inc.
//   "NKE",     // Nike Inc.
//   "SBUX",    // Starbucks Corp.
//   "MCD",     // McDonald’s Corp.

//   // Healthcare
//   "UNH",     // UnitedHealth Group Inc.
//   "JNJ",     // Johnson & Johnson
//   "PFE",     // Pfizer Inc.
//   "MRK",     // Merck & Co. Inc.
//   "ABBV",    // AbbVie Inc.
//   "LLY",     // Eli Lilly and Co.
//   "BMY",     // Bristol-Myers Squibb Co.

//   // Consumer Staples
//   "PG",      // Procter & Gamble Co.
//   "KO",      // Coca-Cola Co.
//   "PEP",     // PepsiCo Inc.
//   "PM",      // Philip Morris International Inc.
//   "MO",      // Altria Group Inc.

//   // Energy
//   "XOM",     // Exxon Mobil Corp.
//   "CVX",     // Chevron Corp.
//   "COP",     // ConocoPhillips
//   "SLB",     // Schlumberger Ltd.
//   "EOG",     // EOG Resources Inc.

//   // Industrials / Other
//   "UPS",     // United Parcel Service Inc.
//   "FDX",     // FedEx Corp.
//   "CAT",     // Caterpillar Inc.
//   "DE",      // Deere & Co.
//   "BA",      // Boeing Co.
//   "LMT",     // Lockheed Martin Corp.
//   "GE",      // General Electric Co.

//   // Telecom & Others
//   "VZ",      // Verizon Communications Inc.
//   "T",       // AT&T Inc.
//   "TMUS",    // T-Mobile US Inc.
  
//   // ETF
//   "SPY",     // S&P 500
//   "QQQ",     // Nasdaq-100
//   "DIA",     // Dow Jones
//   "VTI",     // Total U.S. Market
//   "VOO",     // Vanguard S&P 500
//   "ARKK",    // ARK Innovation ETF
//   "XLK",     // Tech Select Sector
//   "XLF",     // Financials Sector
//   "XLE",     // Energy Sector
//   "IWM",     // Russell 2000 (small-cap)

//   // Space & Aerospace Stocks
//   "SPCE",    // Virgin Galactic
//   "RKLB",    // Rocket Lab USA
//   "MAXR",    // Maxar Technologies (acquired, delisted from NYSE)
//   "ASTR",    // Astra Space Inc.
//   "LHX",     // L3Harris Technologies
//   "NOC",     // Northrop Grumman
//   "BA",      // Boeing Co. (also in aerospace)
//   "LMT",     // Lockheed Martin (space division)
//   "IRDM",    // Iridium Communications
//   "SIRI",    // SiriusXM (satellite)
//   "PL",      // Planet Labs
// ];

// export default function Home() {
//   const [query, setQuery] = useState("");
//   const [stocks, setStocks] = useState<Stock[]>([]);
//   const [suggestions, setSuggestions] = useState<Stock[]>([]);

//   // Fetch stocks on component mount
//   useEffect(() => {
//     const fetchStocks = async () => {
//       try {
//         const response = await fetch("/api/finnhub-stocks");
//         const data = await response.json();
//         if (response.ok) {
//           setStocks(data);
//         } else {
//           console.error("Error fetching stocks:", data.error);
//         }
//       } catch (error) {
//         console.error("Error fetching stocks:", error);
//       }
//     };
//     fetchStocks();
//   }, []);

//   // Get suggestions based on user input (symbol or name starts with input, only after 2nd letter)
//   const getSuggestions = (value: string) => {
//     const inputValue = value.trim().toLowerCase();
//     if (inputValue.length === 0) return []; // No suggestions until 2nd letter

//     // Filter stocks by symbol or name starting with input
//     const filteredStocks = stocks.reduce(
//       (acc, stock) => {
//         if (stock.symbol.toLowerCase().startsWith(inputValue)) {
//           acc.symbolMatches.push(stock);
//         } else if (stock.name.toLowerCase().startsWith(inputValue)) {
//           acc.nameMatches.push(stock);
//         }
//         return acc;
//       },
//       { symbolMatches: [], nameMatches: [] } as {
//         symbolMatches: Stock[];
//         nameMatches: Stock[];
//       }
//     );

//     // Sort each group: prioritize popular symbols, then alphabetically by symbol
//     const sortStocks = (stocks: Stock[]) =>
//       stocks.sort((a, b) => {
//         const aIsPopular = POPULAR_SYMBOLS.includes(a.symbol);
//         const bIsPopular = POPULAR_SYMBOLS.includes(b.symbol);
//         if (aIsPopular && !bIsPopular) return -1;
//         if (!aIsPopular && bIsPopular) return 1;
//         return a.symbol.localeCompare(b.symbol);
//       });

//     // Combine symbol matches (first) and name matches (second)
//     return [
//       ...sortStocks(filteredStocks.symbolMatches),
//       ...sortStocks(filteredStocks.nameMatches),
//     ];
//   };

//   // Autosuggest event handlers
//   const onSuggestionsFetchRequested = ({ value }: { value: string }) => {
//     setSuggestions(getSuggestions(value));
//   };

//   const onSuggestionsClearRequested = () => {
//     setSuggestions([]);
//   };

//   const onChange = (
//     event: React.FormEvent<HTMLElement>,
//     { newValue }: { newValue: string }
//   ) => {
//     setQuery(newValue);
//   };

//   const onSuggestionSelected = (
//     event: React.FormEvent<HTMLElement>,
//     { suggestion }: { suggestion: Stock }
//   ) => {
//     setQuery(suggestion.symbol);
//   };

//   // Render suggestion item (symbol and name)
//   const renderSuggestion = (suggestion: Stock) => (
//     <div className="p-2 hover:bg-gray-100 cursor-pointer">
//       <span className="font-medium">{suggestion.symbol}</span> - {suggestion.name}
//     </div>
//   );

//   // Autosuggest input props
//   const inputProps = {
//     placeholder: "Search for a stock symbol or company...",
//     value: query,
//     onChange,
//     className:
//       "w-full p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500",
//   };

//   return (
//     <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-100">
//       <h1 className="text-4xl font-bold text-center mb-8">Best Website NA</h1>
//       <div className="w-full max-w-md">
//         <Autosuggest
//           suggestions={suggestions}
//           onSuggestionsFetchRequested={onSuggestionsFetchRequested}
//           onSuggestionsClearRequested={onSuggestionsClearRequested}
//           getSuggestionValue={(suggestion: Stock) => suggestion.symbol}
//           renderSuggestion={renderSuggestion}
//           inputProps={inputProps}
//           theme={{
//             container: "relative",
//             suggestionsContainer:
//               "absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto",
//             suggestionHighlighted: "bg-gray-100",
//           }}
//         />
//       </div>
//     </div>
//   );
// }



"use client";

import { useState } from "react";
import Autosuggest from "react-autosuggest";
import { useRouter } from "next/navigation";

interface Stock {
  symbol: string;
  name: string;
}

// List of popular stock symbols
const POPULAR_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "NFLX", "INTC",
  "AMD", "CRM", "ORCL", "IBM", "ADBE", "CSCO", "JPM", "BAC", "WFC", "C", "GS",
  "MS", "AXP", "WMT", "TGT", "COST", "HD", "LOW", "NKE", "SBUX", "MCD", "UNH",
  "JNJ", "PFE", "MRK", "ABBV", "LLY", "BMY", "PG", "KO", "PEP", "PM", "MO", "XOM",
  "CVX", "COP", "SLB", "EOG", "UPS", "FDX", "CAT", "DE", "BA", "LMT", "GE", "VZ",
  "T", "TMUS", "SPY", "QQQ", "DIA", "VTI", "VOO", "ARKK", "XLK", "XLF", "XLE",
  "IWM", "SPCE", "RKLB", "MAXR", "ASTR", "LHX", "NOC", "IRDM", "SIRI", "PL",
];

export default function Home() {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Stock[]>([]);
  const router = useRouter();

  // Get suggestions based on user input
  const getSuggestions = (value: string) => {
    const inputValue = value.trim().toLowerCase();
    if (inputValue.length === 0) return [];

    return POPULAR_SYMBOLS
      .filter((symbol) => symbol.toLowerCase().startsWith(inputValue))
      .map((symbol) => ({ symbol, name: symbol }))
      .sort((a, b) => {
        const aIsPopular = POPULAR_SYMBOLS.includes(a.symbol);
        const bIsPopular = POPULAR_SYMBOLS.includes(b.symbol);
        if (aIsPopular && !bIsPopular) return -1;
        if (!aIsPopular && bIsPopular) return 1;
        return a.symbol.localeCompare(b.symbol);
      });
  };

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
    router.push(`/${suggestion.symbol}`); // Navigate to stock detail page
  };

  // Handle Enter key press
  const onKeyPress = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && query && POPULAR_SYMBOLS.includes(query.toUpperCase())) {
      router.push(`/${query.toUpperCase()}`); // Navigate on Enter if valid symbol
    }
  };

  // Render suggestion item
  const renderSuggestion = (suggestion: Stock) => (
    <div className="p-2 hover:bg-gray-100 cursor-pointer">
      <span className="font-medium">{suggestion.symbol}</span>
    </div>
  );

  // Autosuggest input props
  const inputProps = {
    placeholder: "Search for a stock symbol...",
    value: query,
    onChange,
    onKeyPress, // Add Enter key handler
    className:
      "w-full p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500",
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 bg-gray-100">
      <h1 className="text-4xl font-bold text-center mb-8">Best Website NA</h1>
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