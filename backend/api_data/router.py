from __future__ import annotations

import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import APIRouter, Query


router = APIRouter(prefix="/api/api-data", tags=["API对接-行情数据"])

EASTMONEY_SUGGEST_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://quote.eastmoney.com/",
}


def ok(data: Any, message: str = "ok") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def _http_get_text(url: str, timeout: int = 5, encoding: str = "utf-8") -> str:
    request = Request(url, headers=HTTP_HEADERS)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - trusted quote endpoints configured here.
        return response.read().decode(encoding, errors="ignore")


def _market_prefix(symbol: str) -> str:
    code = symbol[-6:]
    if code.startswith(("6", "9")):
        return "sh"
    if code.startswith(("4", "8")):
        return "bj"
    return "sz"


def _exchange(symbol: str) -> str:
    prefix = _market_prefix(symbol)
    return {"sh": "SH", "sz": "SZ", "bj": "BJ"}.get(prefix, "")


def _decimal_text(value: Any) -> str:
    try:
        decimal = Decimal(str(value or "0").strip())
    except (InvalidOperation, ValueError):
        return ""
    if decimal <= 0:
        return ""
    return f"{decimal:.4f}"


def _int_value(value: Any) -> int:
    try:
        return int(float(str(value or "0")))
    except (TypeError, ValueError):
        return 0


def _security_from_suggest_item(item: dict[str, Any]) -> dict[str, Any]:
    code = str(item.get("Code") or item.get("UnifiedCode") or "").strip()
    quote_id = str(item.get("QuoteID") or "").strip()
    return {
        "symbol": code,
        "name": str(item.get("Name") or "").strip(),
        "exchange": _exchange(code),
        "quote_id": quote_id,
        "security_type": str(item.get("SecurityTypeName") or item.get("Classify") or "").strip(),
        "source": "eastmoney_suggest",
    }


def search_securities(keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    text = keyword.strip()
    if not text:
        return []
    url = (
        "https://searchapi.eastmoney.com/api/suggest/get"
        f"?input={quote(text)}&type=14&token={EASTMONEY_SUGGEST_TOKEN}&count={limit}"
    )
    try:
        payload = json.loads(_http_get_text(url))
    except Exception:
        return []
    rows = (((payload or {}).get("QuotationCodeTable") or {}).get("Data") or [])[:limit]
    return [
        security
        for item in rows
        for security in [_security_from_suggest_item(item)]
        if security["symbol"]
    ]


def fetch_tencent_quote(symbol: str) -> dict[str, Any] | None:
    code = symbol[-6:]
    market_code = f"{_market_prefix(code)}{code}"
    try:
        text = _http_get_text(f"https://qt.gtimg.cn/q={market_code}", encoding="gbk")
    except Exception:
        return None
    match = re.search(r'="([^"]*)"', text)
    if not match:
        return None
    fields = match.group(1).split("~")
    if len(fields) < 35:
        return None
    last_price = _decimal_text(fields[3])
    bid_price_1 = _decimal_text(fields[9]) or last_price
    ask_price_1 = _decimal_text(fields[19]) or last_price
    timestamp = fields[30] if len(fields) > 30 else ""
    bid_levels = [
        {"level": index + 1, "price": _decimal_text(fields[9 + index * 2]), "volume": _int_value(fields[10 + index * 2])}
        for index in range(5)
        if len(fields) > 10 + index * 2 and _decimal_text(fields[9 + index * 2])
    ]
    ask_levels = [
        {"level": index + 1, "price": _decimal_text(fields[19 + index * 2]), "volume": _int_value(fields[20 + index * 2])}
        for index in range(5)
        if len(fields) > 20 + index * 2 and _decimal_text(fields[19 + index * 2])
    ]
    return {
        "symbol": fields[2] or code,
        "name": fields[1] or "",
        "exchange": _exchange(fields[2] or code),
        "last_price": last_price,
        "pre_close": _decimal_text(fields[4]),
        "open_price": _decimal_text(fields[5]),
        "high_price": _decimal_text(fields[33]),
        "low_price": _decimal_text(fields[34]),
        "bid_price_1": bid_price_1,
        "bid_volume_1": _int_value(fields[10]),
        "ask_price_1": ask_price_1,
        "ask_volume_1": _int_value(fields[20]),
        "bid_levels": bid_levels,
        "ask_levels": ask_levels,
        "timestamp": timestamp,
        "source": "tencent_quote",
    }


def build_lookup(keyword: str, side: str = "buy") -> dict[str, Any]:
    text = keyword.strip()
    candidates = search_securities(text, limit=5)
    if not candidates and re.fullmatch(r"\d{6}", text):
        candidates = [{"symbol": text, "name": "", "exchange": _exchange(text), "quote_id": "", "source": "code_rule"}]
    primary = candidates[0] if candidates else {"symbol": text[-6:] if re.fullmatch(r"\d{6}", text[-6:]) else "", "name": text}
    quote_data = fetch_tencent_quote(primary["symbol"]) if primary.get("symbol") else None
    data = {**primary, **(quote_data or {})}
    default_price = data.get("ask_price_1") if side == "buy" else data.get("bid_price_1")
    data.update(
        {
            "query": text,
            "side": side,
            "default_price": default_price or data.get("last_price") or "",
            "default_price_source": "卖一价" if side == "buy" else "买一价",
            "candidates": candidates,
            "resolved_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        }
    )
    return data


@router.get("/symbols")
async def get_symbols(keyword: str = Query(default="", description="证券代码、名称或拼音"), limit: int = Query(default=10, ge=1, le=30)):
    return ok(search_securities(keyword, limit), "证券列表已获取")


@router.get("/kline")
async def get_kline(symbol: str = "BTC/USDT", timeframe: str = "1h"):
    """获取K线数据"""
    return ok([], "模块开发中")


@router.get("/ticker")
async def get_ticker(symbol: str = Query(default="")):
    data = fetch_tencent_quote(symbol[-6:]) if symbol else None
    return ok(data or {}, "实时行情已获取" if data else "未获取到实时行情")


@router.get("/security-lookup")
async def security_lookup(
    keyword: str = Query(..., min_length=1, description="证券代码、名称或拼音"),
    side: str = Query(default="buy", pattern="^(buy|sell)$"),
):
    data = build_lookup(keyword, side)
    return ok(data, "证券信息已识别" if data.get("symbol") else "未识别到证券信息")
