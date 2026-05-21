from sqlalchemy import String, Text, Float, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum

from common.database import Base, TimestampMixin


class MarketType(str, enum.Enum):
    """市场类型"""
    A股 = "A"
    港股 = "HK"
    美股 = "US"


class StockBaseInfoModel(Base, TimestampMixin):
    """个股基础信息表"""
    __tablename__ = "stock_base_info"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="股票代码")
    name: Mapped[str] = mapped_column(String(100), comment="股票名称")
    market: Mapped[str] = mapped_column(String(10), comment="市场类型 A/HK/US")
    sector: Mapped[str] = mapped_column(String(100), nullable=True, comment="所属行业板块")
    IPO_date: Mapped[str] = mapped_column(String(20), nullable=True, comment="上市日期")
    total_shares: Mapped[float] = mapped_column(Float, nullable=True, comment="总股本(万股)")
    float_shares: Mapped[float] = mapped_column(Float, nullable=True, comment="流通股本(万股)")
    status: Mapped[str] = mapped_column(String(20), default="active", comment="状态 active/suspended/delisted")


class KLineDataModel(Base, TimestampMixin):
    """K线数据表"""
    __tablename__ = "kline_data"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True, comment="股票代码")
    timeframe: Mapped[str] = mapped_column(String(10), comment="时间周期 1m/5m/1h/1d")
    timestamp: Mapped[datetime] = mapped_column(comment="K线时间戳")
    open: Mapped[float] = mapped_column(Float, comment="开盘价")
    high: Mapped[float] = mapped_column(Float, comment="最高价")
    low: Mapped[float] = mapped_column(Float, comment="最低价")
    close: Mapped[float] = mapped_column(Float, comment="收盘价")
    volume: Mapped[float] = mapped_column(Float, comment="成交量")
    turnover: Mapped[float] = mapped_column(Float, nullable=True, comment="成交额")

    __table_args__ = (
        # 联合索引：symbol + timeframe + timestamp 唯一
        # Index(...) 可以在这里添加，如果需要
    )


class RealtimeQuoteModel(Base, TimestampMixin):
    """实时行情表"""
    __tablename__ = "realtime_quote"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="股票代码")
    name: Mapped[str] = mapped_column(String(100), comment="股票名称")
    last_price: Mapped[float] = mapped_column(Float, comment="最新价")
    change: Mapped[float] = mapped_column(Float, comment="涨跌额")
    change_pct: Mapped[float] = mapped_column(Float, comment="涨跌幅(%)")
    open: Mapped[float] = mapped_column(Float, comment="开盘价")
    high: Mapped[float] = mapped_column(Float, comment="最高价")
    low: Mapped[float] = mapped_column(Float, comment="最低价")
    volume: Mapped[float] = mapped_column(Float, comment="成交量")
    turnover: Mapped[float] = mapped_column(Float, nullable=True, comment="成交额")
    amplitude: Mapped[float] = mapped_column(Float, nullable=True, comment="振幅(%)")
    market_cap: Mapped[float] = mapped_column(Float, nullable=True, comment="总市值")
    float_market_cap: Mapped[float] = mapped_column(Float, nullable=True, comment="流通市值")
    pe_ratio: Mapped[float] = mapped_column(Float, nullable=True, comment="市盈率")
    pb_ratio: Mapped[float] = mapped_column(Float, nullable=True, comment="市净率")
    timestamp: Mapped[datetime] = mapped_column(comment="数据时间戳")


class SectorInfoModel(Base, TimestampMixin):
    """板块信息表"""
    __tablename__ = "sector_info"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sector_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="板块代码")
    sector_name: Mapped[str] = mapped_column(String(100), comment="板块名称")
    market: Mapped[str] = mapped_column(String(10), comment="市场类型")
    stock_count: Mapped[int] = mapped_column(Integer, default=0, comment="成分股数量")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="板块描述")