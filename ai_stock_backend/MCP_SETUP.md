# Stock Analysis MCP Setup

Phase 5 adds a lightweight MCP-style JSON-RPC endpoint to the existing FastAPI backend:

- Local endpoint: `POST http://127.0.0.1:8001/mcp`
- Info endpoint: `GET http://127.0.0.1:8001/mcp`
- Main stock data source: the same cached `/analysis` pipeline used by the frontend
- OpenAI API cost: none from this server

## Tools

The server advertises these tools:

- `get_stock_analysis`: returns unified trend, valuation, fundamentals, risk, analyst, scoring, and explanation data for a ticker.
- `get_analysis_cache_stats`: shows SQLite cache status.
- `clear_stock_cache`: deletes one ticker from the local analysis cache.

## Run Locally

From the backend folder:

```powershell
cd "C:\Users\eddie\Documents\Summer Project\stockPredictionApp\ai_stock_backend"
..\venv\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Use port `8001` because Windows blocked `8000` on your machine earlier.

## Test With PowerShell

List tools:

```powershell
$body = '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
Invoke-RestMethod -Uri "http://127.0.0.1:8001/mcp" -Method Post -ContentType "application/json" -Body $body
```

Check cache stats:

```powershell
$body = '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_analysis_cache_stats","arguments":{}}}'
Invoke-RestMethod -Uri "http://127.0.0.1:8001/mcp" -Method Post -ContentType "application/json" -Body $body
```

Analyze a stock:

```powershell
$body = '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_stock_analysis","arguments":{"ticker":"AAPL"}}}'
Invoke-RestMethod -Uri "http://127.0.0.1:8001/mcp" -Method Post -ContentType "application/json" -Body $body
```

Force refresh from Yahoo Finance instead of cache:

```powershell
$body = '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_stock_analysis","arguments":{"ticker":"AAPL","force_refresh":true}}}'
Invoke-RestMethod -Uri "http://127.0.0.1:8001/mcp" -Method Post -ContentType "application/json" -Body $body
```

## Connect To ChatGPT Later

OpenAI's Apps SDK uses MCP servers to expose tools to ChatGPT. The official docs say a connector URL should be a reachable HTTPS `/mcp` endpoint, and local development can use an HTTPS tunnel such as Secure MCP Tunnel, ngrok, or Cloudflare Tunnel.

Practical free path:

1. Run the backend locally on `127.0.0.1:8001`.
2. Create a temporary public HTTPS tunnel to `http://127.0.0.1:8001`.
3. In ChatGPT developer mode, create a connector using the tunnel URL plus `/mcp`, for example `https://your-tunnel-url/mcp`.
4. Refresh connector metadata after you change tools.

Useful official docs:

- Apps SDK MCP server concept: https://developers.openai.com/apps-sdk/concepts/mcp-server
- Connect from ChatGPT: https://developers.openai.com/apps-sdk/deploy/connect-chatgpt