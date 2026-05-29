from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class IdMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键")


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class ReviewSession(Base, IdMixin, TimestampMixin):
    __tablename__ = "review_session"
    __table_args__ = (
        UniqueConstraint("session_code", name="uk_review_session_code"),
        Index("idx_review_session_account", "account_id"),
        Index("idx_review_session_strategy", "strategy_id", "version_id"),
        Index("idx_review_session_type_date", "account_type", "start_date", "end_date"),
        Index("idx_review_session_status", "status"),
        {"comment": "复盘会话"},
    )

    session_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="复盘会话编码")
    account_id: Mapped[int | None] = mapped_column(ForeignKey("trading_account.id"), nullable=True, comment="关联账户ID")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="复盘对象类型：live/paper/backtest")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源：live/paper/backtest/replay")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="复盘开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="复盘结束日期")
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="基准指数代码")
    title: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="复盘标题")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="draft", comment="draft/running/done/failed")
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="复盘参数")
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="复盘摘要")


class ReviewMetricSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "review_metric_snapshot"
    __table_args__ = (
        UniqueConstraint("session_id", "metric_key", name="uk_review_metric_session_key"),
        Index("idx_review_metric_session", "session_id"),
        Index("idx_review_metric_key", "metric_key"),
        {"comment": "复盘指标快照"},
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("review_session.id"), nullable=False, comment="所属复盘会话ID")
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="指标编码")
    metric_value: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True, comment="数值型指标值")
    metric_text: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文本型指标值")
    metric_unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="指标单位")
    group_key: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="指标分组")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="指标扩展详情")


class ReviewTradeItem(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "review_trade_item"
    __table_args__ = (
        Index("idx_review_trade_session", "session_id"),
        Index("idx_review_trade_account", "account_id"),
        Index("idx_review_trade_symbol", "symbol"),
        Index("idx_review_trade_date", "trade_date"),
        Index("idx_review_trade_strategy", "strategy_id", "version_id"),
        {"comment": "复盘交易明细"},
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("review_session.id"), nullable=False, comment="所属复盘会话ID")
    account_id: Mapped[int | None] = mapped_column(ForeignKey("trading_account.id"), nullable=True, comment="所属账户ID")
    order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="来源委托ID")
    trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源成交ID")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源：live/paper/backtest/replay")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="运行批次ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    traded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="成交时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交数量")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交金额")
    pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="该笔交易或交易对盈亏")
    pnl_ratio: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True, comment="盈亏比例")
    holding_period_minutes: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="持仓时长，单位分钟")
    signal_tag: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="交易标签")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="复盘明细扩展数据")


class ReviewEquityCurve(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "review_equity_curve"
    __table_args__ = (
        UniqueConstraint("session_id", "curve_date", "curve_time", name="uk_review_equity_point"),
        Index("idx_review_equity_session", "session_id"),
        Index("idx_review_equity_date", "curve_date"),
        {"comment": "复盘净值曲线"},
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("review_session.id"), nullable=False, comment="所属复盘会话ID")
    curve_date: Mapped[date] = mapped_column(Date, nullable=False, comment="曲线日期")
    curve_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="曲线时间点")
    equity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, comment="净值")
    total_asset: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="总资产")
    cash_balance: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="现金余额")
    market_value: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="持仓市值")
    cumulative_return: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True, comment="累计收益率")
    benchmark_value: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True, comment="基准净值")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="曲线点扩展数据")


class ReviewDrawdownCurve(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "review_drawdown_curve"
    __table_args__ = (
        UniqueConstraint("session_id", "curve_date", "curve_time", name="uk_review_drawdown_point"),
        Index("idx_review_drawdown_session", "session_id"),
        Index("idx_review_drawdown_date", "curve_date"),
        {"comment": "复盘回撤曲线"},
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("review_session.id"), nullable=False, comment="所属复盘会话ID")
    curve_date: Mapped[date] = mapped_column(Date, nullable=False, comment="曲线日期")
    curve_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="曲线时间点")
    equity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, comment="当前净值")
    peak_equity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, comment="历史峰值净值")
    drawdown: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False, comment="当前回撤")
    drawdown_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="当前回撤金额")
    peak_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="峰值日期")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="回撤点扩展数据")


class ReviewSuggestion(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "review_suggestion"
    __table_args__ = (
        Index("idx_review_suggestion_session", "session_id"),
        Index("idx_review_suggestion_type", "suggestion_type"),
        Index("idx_review_suggestion_severity", "severity"),
        {"comment": "复盘优化建议"},
    )

    session_id: Mapped[int] = mapped_column(ForeignKey("review_session.id"), nullable=False, comment="所属复盘会话ID")
    suggestion_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="建议类型：risk/position/entry/exit/parameter")
    severity: Mapped[str] = mapped_column(String(16), nullable=False, comment="严重程度：low/medium/high")
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="建议标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="建议正文")
    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="支撑证据")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="open", comment="open/accepted/rejected/resolved")
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="建议负责人")
