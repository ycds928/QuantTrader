"""
Akshare 数据源适配器
使用 akshare 获取真实的 A 股市场数据
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
import logging

import akshare as ak
import pandas as pd

from .base import DataSourceAdapter

logger = logging.getLogger(__name__)


class AkshareAdapter(DataSourceAdapter):
    """Akshare 数据源适配器（真实市场数据）"""

    def __init__(self):
        self._stock_list_cache: Optional[list[dict]] = None
        self._stock_list_cache_time: Optional[datetime] = None
        self._cache_timeout = timedelta(hours=1)

    async def get_stock_base_info(self, symbol: str) -> dict:
        """获取个股基础信息"""
        try:
            df = ak.stock_info_a_code_name()
            row = df[df['code'] == symbol]
            if row.empty:
                return {
                    "symbol": symbol,
                    "name": symbol,
                    "market": "A",
                    "sector": None,
                    "IPO_date": None,
                    "total_shares": None,
                    "float_shares": None,
                    "status": "unknown",
                }
            stock = row.iloc[0]
            return {
                "symbol": str(stock['code']),
                "name": str(stock['name']),
                "market": "A",
                "sector": None,
                "IPO_date": None,
                "total_shares": None,
                "float_shares": None,
                "status": "active",
            }
        except Exception as e:
            logger.error(f"get_stock_base_info error: {e}")
            return {
                "symbol": symbol,
                "name": symbol,
                "market": "A",
                "sector": None,
                "IPO_date": None,
                "total_shares": None,
                "float_shares": None,
                "status": "error",
            }

    async def list_stocks(self, market: Optional[str] = None) -> list[dict]:
        """获取股票列表"""
        # 使用缓存
        if self._stock_list_cache and self._stock_list_cache_time:
            if datetime.now() - self._stock_list_cache_time < self._cache_timeout:
                stocks = self._stock_list_cache
                if market:
                    stocks = [s for s in stocks if s.get("market") == market]
                return stocks

        try:
            df = ak.stock_info_a_code_name()
            stocks = []
            for _, row in df.iterrows():
                code = str(row['code'])
                # 判断市场：沪市以6开头，深市以0、2、3开头
                if code.startswith('6'):
                    mkt = "SH"  # 沪市
                elif code.startswith('0') or code.startswith('2') or code.startswith('3'):
                    mkt = "SZ"  # 深市
                else:
                    mkt = "A"
                stocks.append({
                    "symbol": code,
                    "name": str(row['name']).strip(),
                    "market": "A",
                    "sector": None,
                })

            # 缓存
            self._stock_list_cache = stocks
            self._stock_list_cache_time = datetime.now()

            if market:
                return [s for s in stocks if s.get("market") == market]
            return stocks

        except Exception as e:
            logger.error(f"list_stocks error: {e}")
            return []

    async def get_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """获取K线数据（带重试机制）"""
        # 如果没有指定日期范围，默认获取最近 limit 天
        if not end_date:
            end_date = datetime.now().strftime("%Y%m%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=limit * 2)).strftime("%Y%m%d")

        # 转换 timeframe (支持的级别: 1m/5m/15m/30m/1h/1d/1w)
        period_map = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "1d": "daily",
            "1w": "weekly",
        }
        period = period_map.get(timeframe, "daily")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )

                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
                    return []

                klines = []
                for _, row in df.iterrows():
                    klines.append({
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "timestamp": row['日期'],
                        "open": float(row['开盘']),
                        "high": float(row['最高']),
                        "low": float(row['最低']),
                        "close": float(row['收盘']),
                        "volume": float(row['成交量']),
                        "turnover": float(row.get('成交额', 0)),
                    })

                # 按时间排序
                klines.sort(key=lambda x: x["timestamp"], reverse=True)
                return klines[:limit]

            except Exception as e:
                logger.warning(f"get_kline_data attempt {attempt + 1} failed for {symbol}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"get_kline_data failed after {max_retries} attempts")
                    return []

    async def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情"""
        try:
            # 使用单只股票查询
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=(datetime.now() - timedelta(days=5)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="qfq"
            )

            if df.empty:
                return await self._create_empty_quote(symbol)

            latest = df.iloc[-1]
            prev_close = df.iloc[-2]['收盘'] if len(df) > 1 else latest['收盘']
            change = latest['收盘'] - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0

            return {
                "symbol": symbol,
                "name": symbol,
                "last_price": float(latest['收盘']),
                "change": float(change),
                "change_pct": float(change_pct),
                "open": float(latest['开盘']),
                "high": float(latest['最高']),
                "low": float(latest['最低']),
                "volume": float(latest['成交量']),
                "turnover": float(latest.get('成交额', 0)),
                "amplitude": float(latest.get('振幅', 0)),
                "market_cap": None,
                "float_market_cap": None,
                "pe_ratio": None,
                "pb_ratio": None,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.error(f"get_realtime_quote error for {symbol}: {e}")
            return await self._create_empty_quote(symbol)

    async def _create_empty_quote(self, symbol: str) -> dict:
        """创建空的行情数据"""
        return {
            "symbol": symbol,
            "name": symbol,
            "last_price": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
            "open": 0.0,
            "high": 0.0,
            "low": 0.0,
            "volume": 0.0,
            "turnover": 0.0,
            "amplitude": 0.0,
            "market_cap": None,
            "float_market_cap": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "timestamp": datetime.now(),
        }

    async def get_batch_realtime_quote(self, symbols: list[str]) -> list[dict]:
        """批量获取实时行情"""
        quotes = []
        for symbol in symbols:
            quote = await self.get_realtime_quote(symbol)
            quotes.append(quote)
            # 添加小延迟避免请求过快
            await asyncio.sleep(0.1)
        return quotes

    async def list_sectors(self, market: Optional[str] = None) -> list[dict]:
        """获取板块列表"""
        try:
            df = ak.stock_board_industry_name_em()
            sectors = []
            for _, row in df.iterrows():
                sectors.append({
                    "sector_code": str(row.get('板块代码', '')),
                    "sector_name": str(row.get('板块名称', '')),
                    "market": "A",
                    "stock_count": int(row.get('股票数', 0)),
                    "description": None,
                })
            return sectors
        except Exception as e:
            logger.error(f"list_sectors error: {e}")
            return []

    async def get_sector_stocks(self, sector_code: str) -> list[dict]:
        """获取板块成分股"""
        try:
            df = ak.stock_board_industry_cons_em(symbol=sector_code)
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    "symbol": str(row.get('代码', '')),
                    "name": str(row.get('名称', '')),
                    "market": "A",
                    "sector": sector_code,
                })
            return stocks
        except Exception as e:
            logger.error(f"get_sector_stocks error for {sector_code}: {e}")
            return []

    async def sync_stock_base_info(self, symbols: Optional[list[str]] = None) -> list[dict]:
        """同步个股基础信息"""
        if symbols:
            stocks = []
            for symbol in symbols:
                info = await self.get_stock_base_info(symbol)
                stocks.append(info)
                await asyncio.sleep(0.1)
            return stocks
        else:
            return await self.list_stocks()

    async def sync_kline_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """同步K线数据"""
        return await self.get_kline_data(symbol, timeframe, start_date, end_date, limit=1000)
