(globalThis.TURBOPACK = globalThis.TURBOPACK || []).push([typeof document === "object" ? document.currentScript : undefined, {

"[project]/app/page.tsx [app-client] (ecmascript)": ((__turbopack_context__) => {
"use strict";

var { g: global, __dirname, k: __turbopack_refresh__, m: module } = __turbopack_context__;
{
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
__turbopack_context__.s({
    "default": (()=>Home)
});
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
(()=>{
    const e = new Error("Cannot find module 'react-autosuggest'");
    e.code = 'MODULE_NOT_FOUND';
    throw e;
})();
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/navigation.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
// List of popular stock symbols
const POPULAR_SYMBOLS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "GOOG",
    "AMZN",
    "TSLA",
    "META",
    "NVDA",
    "NFLX",
    "INTC",
    "AMD",
    "CRM",
    "ORCL",
    "IBM",
    "ADBE",
    "CSCO",
    "JPM",
    "BAC",
    "WFC",
    "C",
    "GS",
    "MS",
    "AXP",
    "WMT",
    "TGT",
    "COST",
    "HD",
    "LOW",
    "NKE",
    "SBUX",
    "MCD",
    "UNH",
    "JNJ",
    "PFE",
    "MRK",
    "ABBV",
    "LLY",
    "BMY",
    "PG",
    "KO",
    "PEP",
    "PM",
    "MO",
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "EOG",
    "UPS",
    "FDX",
    "CAT",
    "DE",
    "BA",
    "LMT",
    "GE",
    "VZ",
    "T",
    "TMUS",
    "SPY",
    "QQQ",
    "DIA",
    "VTI",
    "VOO",
    "ARKK",
    "XLK",
    "XLF",
    "XLE",
    "IWM",
    "SPCE",
    "RKLB",
    "MAXR",
    "ASTR",
    "LHX",
    "NOC",
    "IRDM",
    "SIRI",
    "PL"
];
function Home() {
    _s();
    const [query, setQuery] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])("");
    const [suggestions, setSuggestions] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])([]);
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRouter"])();
    // Get suggestions based on user input
    const getSuggestions = (value)=>{
        const inputValue = value.trim().toLowerCase();
        if (inputValue.length === 0) return [];
        return POPULAR_SYMBOLS.filter((symbol)=>symbol.toLowerCase().startsWith(inputValue)).map((symbol)=>({
                symbol,
                name: symbol
            })).sort((a, b)=>{
            const aIsPopular = POPULAR_SYMBOLS.includes(a.symbol);
            const bIsPopular = POPULAR_SYMBOLS.includes(b.symbol);
            if (aIsPopular && !bIsPopular) return -1;
            if (!aIsPopular && bIsPopular) return 1;
            return a.symbol.localeCompare(b.symbol);
        });
    };
    // Autosuggest event handlers
    const onSuggestionsFetchRequested = ({ value })=>{
        setSuggestions(getSuggestions(value));
    };
    const onSuggestionsClearRequested = ()=>{
        setSuggestions([]);
    };
    const onChange = (event, { newValue })=>{
        setQuery(newValue);
    };
    const onSuggestionSelected = (event, { suggestion })=>{
        setQuery(suggestion.symbol);
        router.push(`/${suggestion.symbol}`); // Navigate to stock detail page
    };
    // Handle Enter key press
    const onKeyPress = (event)=>{
        if (event.key === "Enter" && query && POPULAR_SYMBOLS.includes(query.toUpperCase())) {
            router.push(`/${query.toUpperCase()}`); // Navigate on Enter if valid symbol
        }
    };
    // Render suggestion item
    const renderSuggestion = (suggestion)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
            className: "p-2 hover:bg-gray-100 cursor-pointer",
            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                className: "font-medium",
                children: suggestion.symbol
            }, void 0, false, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 317,
                columnNumber: 7
            }, this)
        }, void 0, false, {
            fileName: "[project]/app/page.tsx",
            lineNumber: 316,
            columnNumber: 5
        }, this);
    // Autosuggest input props
    const inputProps = {
        placeholder: "Search for a stock symbol...",
        value: query,
        onChange,
        onKeyPress,
        className: "w-full p-3 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "flex flex-col items-center justify-center min-h-screen p-8 bg-gray-100",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                className: "text-4xl font-bold text-center mb-8",
                children: "Best Website NA"
            }, void 0, false, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 333,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "w-full max-w-md",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(Autosuggest, {
                    suggestions: suggestions,
                    onSuggestionsFetchRequested: onSuggestionsFetchRequested,
                    onSuggestionsClearRequested: onSuggestionsClearRequested,
                    getSuggestionValue: (suggestion)=>suggestion.symbol,
                    renderSuggestion: renderSuggestion,
                    inputProps: inputProps,
                    theme: {
                        container: "relative",
                        suggestionsContainer: "absolute z-10 w-full mt-1 bg-white border rounded-lg shadow-lg max-h-60 overflow-y-auto",
                        suggestionHighlighted: "bg-gray-100"
                    }
                }, void 0, false, {
                    fileName: "[project]/app/page.tsx",
                    lineNumber: 335,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/app/page.tsx",
                lineNumber: 334,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/app/page.tsx",
        lineNumber: 332,
        columnNumber: 5
    }, this);
}
_s(Home, "iXnS1CjF9CDVhxxTKy4BoUKENwE=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRouter"]
    ];
});
_c = Home;
var _c;
__turbopack_context__.k.register(_c, "Home");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(module, globalThis.$RefreshHelpers$);
}
}}),
"[project]/node_modules/next/dist/compiled/react/cjs/react-jsx-dev-runtime.development.js [app-client] (ecmascript)": (function(__turbopack_context__) {

var { g: global, __dirname, m: module, e: exports } = __turbopack_context__;
{
/**
 * @license React
 * react-jsx-dev-runtime.development.js
 *
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */ var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
"use strict";
"production" !== ("TURBOPACK compile-time value", "development") && function() {
    function getComponentNameFromType(type) {
        if (null == type) return null;
        if ("function" === typeof type) return type.$$typeof === REACT_CLIENT_REFERENCE ? null : type.displayName || type.name || null;
        if ("string" === typeof type) return type;
        switch(type){
            case REACT_FRAGMENT_TYPE:
                return "Fragment";
            case REACT_PROFILER_TYPE:
                return "Profiler";
            case REACT_STRICT_MODE_TYPE:
                return "StrictMode";
            case REACT_SUSPENSE_TYPE:
                return "Suspense";
            case REACT_SUSPENSE_LIST_TYPE:
                return "SuspenseList";
            case REACT_ACTIVITY_TYPE:
                return "Activity";
        }
        if ("object" === typeof type) switch("number" === typeof type.tag && console.error("Received an unexpected object in getComponentNameFromType(). This is likely a bug in React. Please file an issue."), type.$$typeof){
            case REACT_PORTAL_TYPE:
                return "Portal";
            case REACT_CONTEXT_TYPE:
                return (type.displayName || "Context") + ".Provider";
            case REACT_CONSUMER_TYPE:
                return (type._context.displayName || "Context") + ".Consumer";
            case REACT_FORWARD_REF_TYPE:
                var innerType = type.render;
                type = type.displayName;
                type || (type = innerType.displayName || innerType.name || "", type = "" !== type ? "ForwardRef(" + type + ")" : "ForwardRef");
                return type;
            case REACT_MEMO_TYPE:
                return innerType = type.displayName || null, null !== innerType ? innerType : getComponentNameFromType(type.type) || "Memo";
            case REACT_LAZY_TYPE:
                innerType = type._payload;
                type = type._init;
                try {
                    return getComponentNameFromType(type(innerType));
                } catch (x) {}
        }
        return null;
    }
    function testStringCoercion(value) {
        return "" + value;
    }
    function checkKeyStringCoercion(value) {
        try {
            testStringCoercion(value);
            var JSCompiler_inline_result = !1;
        } catch (e) {
            JSCompiler_inline_result = !0;
        }
        if (JSCompiler_inline_result) {
            JSCompiler_inline_result = console;
            var JSCompiler_temp_const = JSCompiler_inline_result.error;
            var JSCompiler_inline_result$jscomp$0 = "function" === typeof Symbol && Symbol.toStringTag && value[Symbol.toStringTag] || value.constructor.name || "Object";
            JSCompiler_temp_const.call(JSCompiler_inline_result, "The provided key is an unsupported type %s. This value must be coerced to a string before using it here.", JSCompiler_inline_result$jscomp$0);
            return testStringCoercion(value);
        }
    }
    function getTaskName(type) {
        if (type === REACT_FRAGMENT_TYPE) return "<>";
        if ("object" === typeof type && null !== type && type.$$typeof === REACT_LAZY_TYPE) return "<...>";
        try {
            var name = getComponentNameFromType(type);
            return name ? "<" + name + ">" : "<...>";
        } catch (x) {
            return "<...>";
        }
    }
    function getOwner() {
        var dispatcher = ReactSharedInternals.A;
        return null === dispatcher ? null : dispatcher.getOwner();
    }
    function UnknownOwner() {
        return Error("react-stack-top-frame");
    }
    function hasValidKey(config) {
        if (hasOwnProperty.call(config, "key")) {
            var getter = Object.getOwnPropertyDescriptor(config, "key").get;
            if (getter && getter.isReactWarning) return !1;
        }
        return void 0 !== config.key;
    }
    function defineKeyPropWarningGetter(props, displayName) {
        function warnAboutAccessingKey() {
            specialPropKeyWarningShown || (specialPropKeyWarningShown = !0, console.error("%s: `key` is not a prop. Trying to access it will result in `undefined` being returned. If you need to access the same value within the child component, you should pass it as a different prop. (https://react.dev/link/special-props)", displayName));
        }
        warnAboutAccessingKey.isReactWarning = !0;
        Object.defineProperty(props, "key", {
            get: warnAboutAccessingKey,
            configurable: !0
        });
    }
    function elementRefGetterWithDeprecationWarning() {
        var componentName = getComponentNameFromType(this.type);
        didWarnAboutElementRef[componentName] || (didWarnAboutElementRef[componentName] = !0, console.error("Accessing element.ref was removed in React 19. ref is now a regular prop. It will be removed from the JSX Element type in a future release."));
        componentName = this.props.ref;
        return void 0 !== componentName ? componentName : null;
    }
    function ReactElement(type, key, self, source, owner, props, debugStack, debugTask) {
        self = props.ref;
        type = {
            $$typeof: REACT_ELEMENT_TYPE,
            type: type,
            key: key,
            props: props,
            _owner: owner
        };
        null !== (void 0 !== self ? self : null) ? Object.defineProperty(type, "ref", {
            enumerable: !1,
            get: elementRefGetterWithDeprecationWarning
        }) : Object.defineProperty(type, "ref", {
            enumerable: !1,
            value: null
        });
        type._store = {};
        Object.defineProperty(type._store, "validated", {
            configurable: !1,
            enumerable: !1,
            writable: !0,
            value: 0
        });
        Object.defineProperty(type, "_debugInfo", {
            configurable: !1,
            enumerable: !1,
            writable: !0,
            value: null
        });
        Object.defineProperty(type, "_debugStack", {
            configurable: !1,
            enumerable: !1,
            writable: !0,
            value: debugStack
        });
        Object.defineProperty(type, "_debugTask", {
            configurable: !1,
            enumerable: !1,
            writable: !0,
            value: debugTask
        });
        Object.freeze && (Object.freeze(type.props), Object.freeze(type));
        return type;
    }
    function jsxDEVImpl(type, config, maybeKey, isStaticChildren, source, self, debugStack, debugTask) {
        var children = config.children;
        if (void 0 !== children) if (isStaticChildren) if (isArrayImpl(children)) {
            for(isStaticChildren = 0; isStaticChildren < children.length; isStaticChildren++)validateChildKeys(children[isStaticChildren]);
            Object.freeze && Object.freeze(children);
        } else console.error("React.jsx: Static children should always be an array. You are likely explicitly calling React.jsxs or React.jsxDEV. Use the Babel transform instead.");
        else validateChildKeys(children);
        if (hasOwnProperty.call(config, "key")) {
            children = getComponentNameFromType(type);
            var keys = Object.keys(config).filter(function(k) {
                return "key" !== k;
            });
            isStaticChildren = 0 < keys.length ? "{key: someKey, " + keys.join(": ..., ") + ": ...}" : "{key: someKey}";
            didWarnAboutKeySpread[children + isStaticChildren] || (keys = 0 < keys.length ? "{" + keys.join(": ..., ") + ": ...}" : "{}", console.error('A props object containing a "key" prop is being spread into JSX:\n  let props = %s;\n  <%s {...props} />\nReact keys must be passed directly to JSX without using spread:\n  let props = %s;\n  <%s key={someKey} {...props} />', isStaticChildren, children, keys, children), didWarnAboutKeySpread[children + isStaticChildren] = !0);
        }
        children = null;
        void 0 !== maybeKey && (checkKeyStringCoercion(maybeKey), children = "" + maybeKey);
        hasValidKey(config) && (checkKeyStringCoercion(config.key), children = "" + config.key);
        if ("key" in config) {
            maybeKey = {};
            for(var propName in config)"key" !== propName && (maybeKey[propName] = config[propName]);
        } else maybeKey = config;
        children && defineKeyPropWarningGetter(maybeKey, "function" === typeof type ? type.displayName || type.name || "Unknown" : type);
        return ReactElement(type, children, self, source, getOwner(), maybeKey, debugStack, debugTask);
    }
    function validateChildKeys(node) {
        "object" === typeof node && null !== node && node.$$typeof === REACT_ELEMENT_TYPE && node._store && (node._store.validated = 1);
    }
    var React = __turbopack_context__.r("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)"), REACT_ELEMENT_TYPE = Symbol.for("react.transitional.element"), REACT_PORTAL_TYPE = Symbol.for("react.portal"), REACT_FRAGMENT_TYPE = Symbol.for("react.fragment"), REACT_STRICT_MODE_TYPE = Symbol.for("react.strict_mode"), REACT_PROFILER_TYPE = Symbol.for("react.profiler");
    Symbol.for("react.provider");
    var REACT_CONSUMER_TYPE = Symbol.for("react.consumer"), REACT_CONTEXT_TYPE = Symbol.for("react.context"), REACT_FORWARD_REF_TYPE = Symbol.for("react.forward_ref"), REACT_SUSPENSE_TYPE = Symbol.for("react.suspense"), REACT_SUSPENSE_LIST_TYPE = Symbol.for("react.suspense_list"), REACT_MEMO_TYPE = Symbol.for("react.memo"), REACT_LAZY_TYPE = Symbol.for("react.lazy"), REACT_ACTIVITY_TYPE = Symbol.for("react.activity"), REACT_CLIENT_REFERENCE = Symbol.for("react.client.reference"), ReactSharedInternals = React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE, hasOwnProperty = Object.prototype.hasOwnProperty, isArrayImpl = Array.isArray, createTask = console.createTask ? console.createTask : function() {
        return null;
    };
    React = {
        "react-stack-bottom-frame": function(callStackForError) {
            return callStackForError();
        }
    };
    var specialPropKeyWarningShown;
    var didWarnAboutElementRef = {};
    var unknownOwnerDebugStack = React["react-stack-bottom-frame"].bind(React, UnknownOwner)();
    var unknownOwnerDebugTask = createTask(getTaskName(UnknownOwner));
    var didWarnAboutKeySpread = {};
    exports.Fragment = REACT_FRAGMENT_TYPE;
    exports.jsxDEV = function(type, config, maybeKey, isStaticChildren, source, self) {
        var trackActualOwner = 1e4 > ReactSharedInternals.recentlyCreatedOwnerStacks++;
        return jsxDEVImpl(type, config, maybeKey, isStaticChildren, source, self, trackActualOwner ? Error("react-stack-top-frame") : unknownOwnerDebugStack, trackActualOwner ? createTask(getTaskName(type)) : unknownOwnerDebugTask);
    };
}();
}}),
"[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)": (function(__turbopack_context__) {

var { g: global, __dirname, m: module, e: exports } = __turbopack_context__;
{
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
'use strict';
if ("TURBOPACK compile-time falsy", 0) {
    "TURBOPACK unreachable";
} else {
    module.exports = __turbopack_context__.r("[project]/node_modules/next/dist/compiled/react/cjs/react-jsx-dev-runtime.development.js [app-client] (ecmascript)");
}
}}),
"[project]/node_modules/next/navigation.js [app-client] (ecmascript)": (function(__turbopack_context__) {

var { g: global, __dirname, m: module, e: exports } = __turbopack_context__;
{
module.exports = __turbopack_context__.r("[project]/node_modules/next/dist/client/components/navigation.js [app-client] (ecmascript)");
}}),
}]);

//# sourceMappingURL=_ca37da7f._.js.map