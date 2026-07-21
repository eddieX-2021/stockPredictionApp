from __future__ import annotations

import json
from typing import Any

from app.services.analysis import build_stock_analysis
from app.services.analysis_cache import (
    clear_analysis_cache,
    get_analysis_cache_stats,
    get_or_build_analysis,
)
from app.services.json_safe import json_safe


SERVER_INFO = {
    "name": "stock-trend-analysis",
    "version": "0.5.0",
}

SERVER_INSTRUCTIONS = (
    "Use these tools to analyze public stock trend data. The analysis is educational, "
    "not financial advice. Prefer cached data unless the user explicitly asks for a refresh."
)

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_stock_analysis",
        "title": "Get stock trend analysis",
        "description": (
            "Return the unified stock analysis dashboard data for one ticker, including "
            "price trend, valuation, fundamentals, risk, analyst context, score, and explanation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol, for example AAPL, MSFT, NVDA, or TSLA.",
                },
                "force_refresh": {
                    "type": "boolean",
                    "description": "Bypass the SQLite cache and rebuild from Yahoo Finance.",
                    "default": False,
                },
            },
            "required": ["ticker"],
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
            "openWorldHint": True,
        },
    },
    {
        "name": "get_analysis_cache_stats",
        "title": "Get analysis cache stats",
        "description": "Show local SQLite cache entries, TTL, and approximate payload size.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {
            "readOnlyHint": True,
        },
    },
    {
        "name": "clear_stock_cache",
        "title": "Clear one stock cache",
        "description": "Delete the cached analysis for one ticker so the next call rebuilds it.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol to clear from the analysis cache.",
                }
            },
            "required": ["ticker"],
            "additionalProperties": False,
        },
        "annotations": {
            "destructiveHint": True,
        },
    },
]


def handle_mcp_request(payload: Any) -> Any:
    """Handle a small MCP JSON-RPC surface over the existing FastAPI app."""
    if isinstance(payload, list):
        return [_handle_single_mcp_request(item) for item in payload]
    return _handle_single_mcp_request(payload)


def _handle_single_mcp_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _mcp_error(None, -32600, "Invalid JSON-RPC request.")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    try:
        if method == "initialize":
            return _mcp_success(
                request_id,
                {
                    "protocolVersion": _requested_protocol_version(params),
                    "serverInfo": SERVER_INFO,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "instructions": SERVER_INSTRUCTIONS,
                },
            )

        if method == "tools/list":
            return _mcp_success(request_id, {"tools": MCP_TOOLS})

        if method == "tools/call":
            if not isinstance(params, dict):
                return _mcp_error(request_id, -32602, "tools/call params must be an object.")
            result = call_mcp_tool(params.get("name"), params.get("arguments") or {})
            return _mcp_success(request_id, _tool_result(result))

        return _mcp_error(request_id, -32601, f"Unknown MCP method: {method}")
    except ValueError as exc:
        return _mcp_error(request_id, -32602, str(exc))
    except Exception as exc:
        return _mcp_error(request_id, -32603, f"Tool failed: {exc}")


def call_mcp_tool(name: Any, arguments: Any) -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Tool name is required.")
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")

    if name == "get_stock_analysis":
        ticker = _ticker_from_args(arguments)
        force_refresh = bool(arguments.get("force_refresh", False))
        return get_or_build_analysis(
            ticker,
            build_stock_analysis,
            force_refresh=force_refresh,
        )

    if name == "get_analysis_cache_stats":
        return get_analysis_cache_stats()

    if name == "clear_stock_cache":
        ticker = _ticker_from_args(arguments)
        removed = clear_analysis_cache(ticker)
        return {
            "ticker": ticker,
            "removed": removed,
            "message": f"Analysis cache cleared for {ticker}",
        }

    raise ValueError(f"Unknown tool: {name}")


def _ticker_from_args(arguments: dict[str, Any]) -> str:
    ticker = str(arguments.get("ticker", "")).upper().strip()
    if not ticker:
        raise ValueError("ticker is required.")
    return ticker


def _tool_result(result: dict[str, Any]) -> dict[str, Any]:
    safe_result = json_safe(result)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(safe_result, indent=2),
            }
        ],
        "structuredContent": safe_result,
    }


def _requested_protocol_version(params: Any) -> str:
    if isinstance(params, dict) and isinstance(params.get("protocolVersion"), str):
        return params["protocolVersion"]
    return "2025-03-26"


def _mcp_success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def _mcp_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
