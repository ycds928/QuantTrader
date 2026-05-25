from __future__ import annotations

from datetime import datetime, date
from typing import Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
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


class TradingAccount(Base, IdMixin, TimestampMixin):
    __tablename__ = "trading_account"
    __table_args__ = (
        UniqueConstraint("account_code", name="uk_trading_account_code"),
        Index("idx_trading_account_type", "account_type"),
        Index("idx_trading_account_broker_account_no", "broker_account_no"),
        {"comment": "账户主档"},
    )

    account_code: Mapped[str] = mapped_column(String(64), nullable=False, comment="系统账户编码")
    account_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="账户展示名")
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="live/paper/backtest")
    broker_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="券商或平台名称")
    broker_account_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="资金账号")
    shareholder_account: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="股东账号")
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="交易市场，如 SH/SZ/BJ")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="active", comment="active/inactive/archived")
    is_default: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="是否默认账户")
    meta_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展信息")


class AccountBinding(Base, IdMixin, TimestampMixin):
    __tablename__ = "account_binding"
    __table_args__ = (
        UniqueConstraint("account_id", "binding_type", "client_identity", name="uk_account_binding"),
        Index("idx_account_binding_account_id", "account_id"),
        {"comment": "账户绑定关系"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="关联 trading_account.id")
    binding_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="desktop/ths/webapi/mock")
    client_path: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="桌面客户端路径")
    client_identity: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="客户端唯一标识")
    login_account_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="界面展示的登录名")
    login_account_mask: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="脱敏账号")
    is_active: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="1", comment="是否启用")
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近连接时间")


class AccountRuntimeStatus(Base, IdMixin, TimestampMixin):
    __tablename__ = "account_runtime_status"
    __table_args__ = (
        UniqueConstraint("account_id", name="uk_account_runtime_status_account_id"),
        Index("idx_account_runtime_status_account_id", "account_id"),
        {"comment": "账户运行状态"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="关联 trading_account.id")
    is_connected: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="是否已连接")
    is_ready: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="是否可交易")
    current_source: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="当前数据来源 live/paper/backtest")
    window_title: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="交易客户端窗口标题")
    window_class: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="交易客户端窗口类名")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近同步时间")
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近心跳时间")
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最近错误编码")
    last_error_message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="最近错误消息")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展状态信息")


class AccountOperationTask(Base, IdMixin, TimestampMixin):
    __tablename__ = "account_operation_task"
    __table_args__ = (
        UniqueConstraint("task_no", name="uk_account_operation_task_no"),
        Index("idx_account_operation_task_account_id", "account_id"),
        Index("idx_account_operation_task_status", "status"),
        Index("idx_account_operation_task_type", "operation_type"),
        {"comment": "账户操作任务"},
    )

    task_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="任务编号")
    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="关联 trading_account.id")
    account_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="live/paper/backtest")
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="connect/sync/buy/sell/cancel/query_balance/query_positions/query_orders/query_trades/backtest_run")
    request_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="请求参数")
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="响应结果")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="created", comment="created/running/success/failed/captcha_waiting/manual_intervention_required/timeout")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="错误编码")
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="错误消息")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")


class AccountOperationStep(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "account_operation_step"
    __table_args__ = (
        UniqueConstraint("task_id", "step_index", name="uk_account_operation_step"),
        Index("idx_account_operation_step_task_id", "task_id"),
        {"comment": "账户操作步骤"},
    )

    task_id: Mapped[int] = mapped_column(ForeignKey("account_operation_task.id"), nullable=False, comment="关联 account_operation_task.id")
    step_index: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="步骤序号")
    step_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="步骤名称")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending", comment="pending/running/success/failed/skipped")
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="步骤输入")
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="步骤输出")
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="错误消息")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")


class LiveBalanceSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "live_balance_snapshot"
    __table_args__ = (
        Index("idx_live_balance_account_date", "account_id", "trade_date"),
        Index("idx_live_balance_snapshot_time", "snapshot_time"),
        {"comment": "实盘资金快照"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="实盘账户ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="快照采集时间")
    total_asset: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="总资产")
    cash_balance: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="资金余额")
    available_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="可用资金")
    withdrawable_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="可取资金")
    frozen_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="冻结资金")
    market_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="股票持仓市值")
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="已实现盈亏")
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="未实现盈亏")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源 live/paper/backtest/replay/manual")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始资金数据")


class LivePositionSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "live_position_snapshot"
    __table_args__ = (
        UniqueConstraint("account_id", "trade_date", "symbol", name="uk_live_position"),
        Index("idx_live_position_symbol", "symbol"),
        Index("idx_live_position_time", "snapshot_time"),
        {"comment": "实盘持仓快照"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="实盘账户ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="快照采集时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="交易所代码")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="当前持仓数量")
    available_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="可卖数量")
    frozen_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="冻结数量")
    cost_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="成本价")
    last_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="最新价")
    market_value: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="持仓市值")
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="浮动盈亏")
    pnl_ratio: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True, comment="浮盈比例")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始持仓数据")


class LiveOrder(Base, IdMixin, TimestampMixin):
    __tablename__ = "live_order"
    __table_args__ = (
        UniqueConstraint("order_no", name="uk_live_order_no"),
        UniqueConstraint("broker_order_no", name="uk_live_broker_order_no"),
        Index("idx_live_order_account_date", "account_id", "trade_date"),
        Index("idx_live_order_strategy", "strategy_id", "version_id"),
        Index("idx_live_order_status", "status"),
        Index("idx_live_order_symbol", "symbol"),
        {"comment": "实盘委托"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="实盘账户ID")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略运行批次ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, comment="幂等键")
    order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="系统订单号")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="券商合同编号")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="委托交易日")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="limit", comment="委托类型")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="委托价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="委托数量")
    filled_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="已成交数量")
    canceled_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="已撤数量")
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="成交均价")
    status: Mapped[str] = mapped_column(String(24), nullable=False, comment="订单状态")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="提交时间")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="接受时间")
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="撤单时间")
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="拒单时间")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始委托数据")


class LiveTrade(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "live_trade"
    __table_args__ = (
        UniqueConstraint("trade_id", name="uk_live_trade_id"),
        Index("idx_live_trade_account_date", "account_id", "trade_date"),
        Index("idx_live_trade_order_id", "order_id"),
        Index("idx_live_trade_symbol", "symbol"),
        {"comment": "实盘成交"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="实盘账户ID")
    order_id: Mapped[int | None] = mapped_column(ForeignKey("live_order.id"), nullable=True, comment="关联 live_order.id")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略运行批次ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="系统成交ID")
    broker_trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="券商成交编号")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="券商合同编号")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="成交交易日")
    traded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="成交时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交数量")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交金额")
    commission: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="佣金")
    stamp_tax: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="印花税")
    transfer_fee: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="过户费")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始成交数据")


class LiveOrderStatusLog(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "live_order_status_log"
    __table_args__ = (
        Index("idx_live_order_status_log_order_id", "order_id"),
        Index("idx_live_order_status_log_account_id", "account_id"),
        {"comment": "实盘订单状态流水"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="实盘账户ID")
    order_id: Mapped[int] = mapped_column(ForeignKey("live_order.id"), nullable=False, comment="关联 live_order.id")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="券商合同编号")
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True, comment="变化前状态")
    to_status: Mapped[str] = mapped_column(String(24), nullable=False, comment="变化后状态")
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="submit/accept/partial_fill/fill/cancel_request/cancel_success/reject/fail/sync_update")
    event_source: Mapped[str] = mapped_column(String(32), nullable=False, comment="ths_desktop/paper_engine/backtest_engine/manual_sync/strategy_engine")
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="事件时间")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="事件详情")
    message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="事件说明")


class PaperBalanceSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "paper_balance_snapshot"
    __table_args__ = (
        Index("idx_paper_balance_account_date", "account_id", "trade_date"),
        Index("idx_paper_balance_snapshot_time", "snapshot_time"),
        {"comment": "模拟盘资金快照"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="快照采集时间")
    total_asset: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="总资产")
    cash_balance: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="资金余额")
    available_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="可用资金")
    withdrawable_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="可取资金")
    frozen_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="冻结资金")
    market_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="股票持仓市值")
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="已实现盈亏")
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="未实现盈亏")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始资金数据")


class PaperPositionSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "paper_position_snapshot"
    __table_args__ = (
        UniqueConstraint("account_id", "trade_date", "symbol", name="uk_paper_position"),
        Index("idx_paper_position_symbol", "symbol"),
        Index("idx_paper_position_time", "snapshot_time"),
        {"comment": "模拟盘持仓快照"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="快照采集时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="交易所代码")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="当前持仓数量")
    available_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="可卖数量")
    frozen_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="冻结数量")
    cost_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="成本价")
    last_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="最新价")
    market_value: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="持仓市值")
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="浮动盈亏")
    pnl_ratio: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True, comment="浮盈比例")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始持仓数据")


class PaperOrder(Base, IdMixin, TimestampMixin):
    __tablename__ = "paper_order"
    __table_args__ = (
        UniqueConstraint("order_no", name="uk_paper_order_no"),
        UniqueConstraint("broker_order_no", name="uk_paper_broker_order_no"),
        Index("idx_paper_order_account_date", "account_id", "trade_date"),
        Index("idx_paper_order_strategy", "strategy_id", "version_id"),
        Index("idx_paper_order_status", "status"),
        Index("idx_paper_order_symbol", "symbol"),
        {"comment": "模拟盘委托"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模拟运行批次ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, comment="幂等键")
    order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="系统订单号")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模拟合同编号")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="委托交易日")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="limit", comment="委托类型")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="委托价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="委托数量")
    filled_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="已成交数量")
    canceled_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="已撤数量")
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="成交均价")
    status: Mapped[str] = mapped_column(String(24), nullable=False, comment="订单状态")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="提交时间")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="接受时间")
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="撤单时间")
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="拒单时间")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始委托数据")


class PaperTrade(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "paper_trade"
    __table_args__ = (
        UniqueConstraint("trade_id", name="uk_paper_trade_id"),
        Index("idx_paper_trade_account_date", "account_id", "trade_date"),
        Index("idx_paper_trade_order_id", "order_id"),
        Index("idx_paper_trade_symbol", "symbol"),
        {"comment": "模拟盘成交"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    order_id: Mapped[int | None] = mapped_column(ForeignKey("paper_order.id"), nullable=True, comment="关联 paper_order.id")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模拟运行批次ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="系统成交ID")
    broker_trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模拟成交编号")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模拟合同编号")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="成交交易日")
    traded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="成交时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交数量")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交金额")
    commission: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="佣金")
    stamp_tax: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="印花税")
    transfer_fee: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="过户费")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始成交数据")


class PaperOrderStatusLog(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "paper_order_status_log"
    __table_args__ = (
        Index("idx_paper_order_status_log_order_id", "order_id"),
        Index("idx_paper_order_status_log_account_id", "account_id"),
        {"comment": "模拟盘订单状态流水"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    order_id: Mapped[int] = mapped_column(ForeignKey("paper_order.id"), nullable=False, comment="关联 paper_order.id")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="模拟合同编号")
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True, comment="变化前状态")
    to_status: Mapped[str] = mapped_column(String(24), nullable=False, comment="变化后状态")
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="submit/accept/partial_fill/fill/cancel_request/cancel_success/reject/fail/sync_update")
    event_source: Mapped[str] = mapped_column(String(32), nullable=False, comment="paper_engine/manual_sync/strategy_engine")
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="事件时间")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="事件详情")
    message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="事件说明")


class BacktestRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "backtest_run"
    __table_args__ = (
        UniqueConstraint("run_id", name="uk_backtest_run_id"),
        Index("idx_backtest_strategy", "strategy_id", "version_id"),
        Index("idx_backtest_date", "start_date", "end_date"),
        {"comment": "回测运行批次"},
    )

    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    account_id: Mapped[int | None] = mapped_column(ForeignKey("trading_account.id"), nullable=True, comment="回测账户ID")
    strategy_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    start_date: Mapped[date] = mapped_column(Date, nullable=False, comment="回测开始日期")
    end_date: Mapped[date] = mapped_column(Date, nullable=False, comment="回测结束日期")
    initial_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="初始资金")
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="基准指数代码")
    frequency: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="回测频率")
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="策略参数")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="created", comment="created/running/done/failed")


class BacktestBalanceSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "backtest_balance_snapshot"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["backtest_run.run_id"]),
        Index("idx_backtest_balance_account_date", "account_id", "trade_date"),
        Index("idx_backtest_balance_snapshot_time", "snapshot_time"),
        {"comment": "回测资金快照"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="回测账户ID")
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="快照采集时间")
    total_asset: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="总资产")
    cash_balance: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="资金余额")
    available_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="可用资金")
    withdrawable_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="可取资金")
    frozen_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="冻结资金")
    market_value: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, server_default="0", comment="股票持仓市值")
    realized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="已实现盈亏")
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="未实现盈亏")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始资金数据")


class BacktestPositionSnapshot(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "backtest_position_snapshot"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["backtest_run.run_id"]),
        UniqueConstraint("account_id", "run_id", "trade_date", "symbol", name="uk_backtest_position"),
        Index("idx_backtest_position_symbol", "symbol"),
        Index("idx_backtest_position_time", "snapshot_time"),
        {"comment": "回测持仓快照"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="回测账户ID")
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="交易日期")
    snapshot_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="快照采集时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="交易所代码")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="当前持仓数量")
    available_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="可卖数量")
    frozen_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="冻结数量")
    cost_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="成本价")
    last_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="最新价")
    market_value: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="持仓市值")
    unrealized_pnl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="浮动盈亏")
    pnl_ratio: Mapped[float | None] = mapped_column(Numeric(20, 6), nullable=True, comment="浮盈比例")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始持仓数据")


class BacktestOrder(Base, IdMixin, TimestampMixin):
    __tablename__ = "backtest_order"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["backtest_run.run_id"]),
        UniqueConstraint("order_no", name="uk_backtest_order_no"),
        UniqueConstraint("broker_order_no", name="uk_backtest_broker_order_no"),
        Index("idx_backtest_order_account_date", "account_id", "trade_date"),
        Index("idx_backtest_order_strategy", "strategy_id", "version_id"),
        Index("idx_backtest_order_status", "status"),
        Index("idx_backtest_order_symbol", "symbol"),
        {"comment": "回测委托"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="回测账户ID")
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    idempotency_key: Mapped[str | None] = mapped_column(String(80), nullable=True, comment="幂等键")
    order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="系统订单号")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="回测合同编号")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="委托交易日")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    order_type: Mapped[str] = mapped_column(String(16), nullable=False, server_default="limit", comment="委托类型")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="委托价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="委托数量")
    filled_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="已成交数量")
    canceled_quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0", comment="已撤数量")
    avg_fill_price: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="成交均价")
    status: Mapped[str] = mapped_column(String(24), nullable=False, comment="订单状态")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    source: Mapped[str] = mapped_column(String(16), nullable=False, comment="数据来源")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="提交时间")
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="接受时间")
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="撤单时间")
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="拒单时间")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始委托数据")


class BacktestTrade(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "backtest_trade"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["backtest_run.run_id"]),
        UniqueConstraint("trade_id", name="uk_backtest_trade_id"),
        Index("idx_backtest_trade_account_date", "account_id", "trade_date"),
        Index("idx_backtest_trade_order_id", "order_id"),
        Index("idx_backtest_trade_symbol", "symbol"),
        {"comment": "回测成交"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="回测账户ID")
    order_id: Mapped[int | None] = mapped_column(ForeignKey("backtest_order.id"), nullable=True, comment="关联 backtest_order.id")
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    signal_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略信号ID")
    trade_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="系统成交ID")
    broker_trade_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="回测成交编号")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="回测合同编号")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="成交交易日")
    traded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="成交时间")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, comment="证券代码")
    name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="证券名称")
    side: Mapped[str] = mapped_column(String(8), nullable=False, comment="buy/sell")
    price: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交价格")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="成交数量")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="成交金额")
    commission: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="佣金")
    stamp_tax: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="印花税")
    transfer_fee: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="过户费")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始成交数据")


class BacktestOrderStatusLog(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "backtest_order_status_log"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["backtest_run.run_id"]),
        Index("idx_backtest_order_status_log_order_id", "order_id"),
        Index("idx_backtest_order_status_log_account_id", "account_id"),
        {"comment": "回测订单状态流水"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="回测账户ID")
    order_id: Mapped[int] = mapped_column(ForeignKey("backtest_order.id"), nullable=False, comment="关联 backtest_order.id")
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    broker_order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="回测合同编号")
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True, comment="变化前状态")
    to_status: Mapped[str] = mapped_column(String(24), nullable=False, comment="变化后状态")
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="submit/accept/partial_fill/fill/cancel_request/cancel_success/reject/fail/sync_update")
    event_source: Mapped[str] = mapped_column(String(32), nullable=False, comment="backtest_engine/manual_sync/strategy_engine")
    event_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="事件时间")
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="事件详情")
    message: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="事件说明")


class LiveCashFlow(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "live_cash_flow"
    __table_args__ = (
        Index("idx_live_cash_account_date", "account_id", "trade_date"),
        Index("idx_live_cash_ref", "ref_type", "ref_id"),
        {"comment": "实盘现金流水"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="实盘账户ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="发生日期")
    flow_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="流水类型：deposit/withdraw/freeze/unfreeze/trade_fee/tax/trade_cash")
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="关联对象类型：order/trade/manual")
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联对象ID或编号")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="流水金额，收入为正，支出为负")
    balance_after: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="流水发生后的资金余额")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始流水数据")


class PaperCashFlow(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "paper_cash_flow"
    __table_args__ = (
        Index("idx_paper_cash_account_date", "account_id", "trade_date"),
        Index("idx_paper_cash_ref", "ref_type", "ref_id"),
        {"comment": "模拟盘现金流水"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="发生日期")
    flow_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="流水类型：deposit/withdraw/freeze/unfreeze/trade_fee/tax/trade_cash")
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="关联对象类型：order/trade/manual")
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联对象ID或编号")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="流水金额，收入为正，支出为负")
    balance_after: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="流水发生后的资金余额")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始流水数据")


class BacktestCashFlow(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "backtest_cash_flow"
    __table_args__ = (
        ForeignKeyConstraint(["run_id"], ["backtest_run.run_id"]),
        Index("idx_backtest_cash_account_date", "account_id", "trade_date"),
        Index("idx_backtest_cash_run_date", "run_id", "trade_date"),
        Index("idx_backtest_cash_ref", "ref_type", "ref_id"),
        {"comment": "回测现金流水"},
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="回测账户ID")
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="回测运行批次ID")
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, comment="发生日期")
    flow_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="流水类型：deposit/withdraw/freeze/unfreeze/trade_fee/tax/trade_cash")
    ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="关联对象类型：order/trade/manual")
    ref_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="关联对象ID或编号")
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="流水金额，收入为正，支出为负")
    balance_after: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True, comment="流水发生后的资金余额")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="备注")
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始流水数据")


class PaperSimulationRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "paper_simulation_run"
    __table_args__ = (
        UniqueConstraint("run_id", name="uk_paper_simulation_run_id"),
        Index("idx_paper_simulation_account", "account_id"),
        Index("idx_paper_simulation_strategy", "strategy_id", "version_id"),
        Index("idx_paper_simulation_date", "start_date", "end_date"),
        {"comment": "模拟盘运行批次"},
    )

    run_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="模拟运行批次ID")
    account_id: Mapped[int] = mapped_column(ForeignKey("trading_account.id"), nullable=False, comment="模拟盘账户ID")
    strategy_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略ID")
    version_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="策略版本ID")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="模拟开始日期")
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="模拟结束日期")
    initial_cash: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False, comment="初始资金")
    benchmark_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="基准指数代码")
    frequency: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="模拟频率，如 daily/1m/5m")
    market_data_source: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="行情源")
    matching_rule: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="撮合规则")
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="模拟参数")
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="created", comment="created/running/done/failed/canceled")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="结束时间")
    summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="模拟结果摘要")
