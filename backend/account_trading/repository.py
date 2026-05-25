from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AccountBinding,
    AccountOperationStep,
    AccountOperationTask,
    AccountRuntimeStatus,
    BacktestOrder,
    BacktestTrade,
    LiveBalanceSnapshot,
    LiveOrder,
    LiveOrderStatusLog,
    LivePositionSnapshot,
    LiveTrade,
    PaperBalanceSnapshot,
    PaperOrder,
    PaperOrderStatusLog,
    PaperPositionSnapshot,
    PaperTrade,
    TradingAccount,
)
from .paper_engine import PaperOrderRequest, PaperTradingEngine


def _now() -> datetime:
    return datetime.now()


def _today() -> date:
    return date.today()


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _int(value: Any) -> int:
    try:
        return int(float(str(value or "0").replace(",", "")))
    except (TypeError, ValueError):
        return 0


def _parse_datetime(value: Any, trade_date: date | None = None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    text = str(value or "").strip()
    if not text:
        return None

    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%H:%M:%S",
        "%H:%M",
        "%Y%m%d",
    ]
    for fmt in candidates:
        try:
            parsed = datetime.strptime(text, fmt)
            if fmt.startswith("%H") and trade_date:
                return datetime.combine(trade_date, parsed.time())
            return parsed
        except ValueError:
            continue
    return None


def _normalize_account_type(value: Any) -> str:
    text = str(value or "").lower()
    if text in {"paper", "live", "backtest"}:
        return text
    if "模拟" in text:
        return "paper"
    return "live"


def _normalize_order_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    mapping = {
        "已报": "submitted",
        "未报": "created",
        "已成": "filled",
        "部成": "partial_filled",
        "部撤": "canceled",
        "已撤": "canceled",
        "废单": "rejected",
        "失败": "failed",
        "submitted": "submitted",
        "confirmed": "submitted",
        "accepted": "accepted",
        "partial_filled": "partial_filled",
        "filled": "filled",
        "canceled": "canceled",
        "rejected": "rejected",
        "failed": "failed",
        "unconfirmed": "failed",
    }
    return mapping.get(text, text or "submitted")


def _account_code(account_info: dict[str, Any]) -> str:
    account_type = _normalize_account_type(account_info.get("account_type"))
    capital_account = str(account_info.get("capital_account") or "").strip()
    shareholder_account = str(account_info.get("shareholder_account") or "").strip()
    raw = capital_account or shareholder_account or "LOCAL"
    return f"{account_type.upper()}_THS_{raw.replace('*', 'X')}"


def _clean_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _loaded_value(obj: Any, name: str, default: Any = None) -> Any:
    return inspect(obj).dict.get(name, default)


def _datetime_text(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return None


class AccountTradingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_accounts(self) -> list[dict[str, Any]]:
        result = await self.db.execute(select(TradingAccount).order_by(TradingAccount.is_default.desc(), TradingAccount.id.desc()))
        accounts = result.scalars().all()
        if not accounts:
            return []

        account_ids = [account.id for account in accounts]
        binding_result = await self.db.execute(select(AccountBinding).where(AccountBinding.account_id.in_(account_ids)))
        runtime_result = await self.db.execute(select(AccountRuntimeStatus).where(AccountRuntimeStatus.account_id.in_(account_ids)))

        bindings_by_account: dict[int, list[AccountBinding]] = {}
        for binding in binding_result.scalars().all():
            bindings_by_account.setdefault(binding.account_id, []).append(binding)

        runtime_by_account = {row.account_id: row for row in runtime_result.scalars().all()}
        return [self._serialize_account(account, bindings_by_account.get(account.id, []), runtime_by_account.get(account.id)) for account in accounts]

    async def get_account(self, account_id: int) -> TradingAccount | None:
        result = await self.db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
        return result.scalar_one_or_none()

    async def list_order_records(self, account: TradingAccount, scope: str = "today") -> list[dict[str, Any]]:
        order_cls = self._order_cls(account)
        query = select(order_cls).where(order_cls.account_id == account.id)
        if scope == "today":
            query = query.where(order_cls.trade_date == _today())
        query = query.order_by(order_cls.submitted_at.desc(), order_cls.id.desc()).limit(500)
        result = await self.db.execute(query)
        return [self._serialize_order(row) for row in result.scalars().all()]

    async def list_trade_records(self, account: TradingAccount, scope: str = "today") -> list[dict[str, Any]]:
        trade_cls = self._trade_cls(account)
        query = select(trade_cls).where(trade_cls.account_id == account.id)
        if scope == "today":
            query = query.where(trade_cls.trade_date == _today())
        query = query.order_by(trade_cls.traded_at.desc(), trade_cls.id.desc()).limit(500)
        result = await self.db.execute(query)
        return [self._serialize_trade(row) for row in result.scalars().all()]

    async def get_latest_balance(self, account: TradingAccount) -> dict[str, Any]:
        if account.account_type == "paper":
            result = await self.db.execute(
                select(PaperBalanceSnapshot)
                .where(PaperBalanceSnapshot.account_id == account.id)
                .order_by(PaperBalanceSnapshot.snapshot_time.desc(), PaperBalanceSnapshot.id.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is not None:
                return self._serialize_balance(row)
            initial_cash = _decimal((account.meta_json or {}).get("initial_cash"))
            return self._balance_payload(initial_cash, Decimal("0"), initial_cash)
        raise LookupError("当前账户类型不支持本地资金查询")

    async def list_latest_positions(self, account: TradingAccount) -> list[dict[str, Any]]:
        if account.account_type != "paper":
            raise LookupError("当前账户类型不支持本地持仓查询")
        result = await self.db.execute(
            select(PaperPositionSnapshot)
            .where(PaperPositionSnapshot.account_id == account.id)
            .order_by(PaperPositionSnapshot.snapshot_time.desc(), PaperPositionSnapshot.id.desc())
        )
        latest_by_symbol: dict[str, PaperPositionSnapshot] = {}
        for row in result.scalars().all():
            if row.symbol not in latest_by_symbol:
                latest_by_symbol[row.symbol] = row
        return [
            self._serialize_position(row)
            for row in latest_by_symbol.values()
            if int(row.quantity or 0) > 0
        ]

    async def refresh_paper_market_value(self, account: TradingAccount) -> dict[str, Any]:
        if account.account_type != "paper":
            raise ValueError("当前账户不是模拟账户")
        positions = await self._latest_paper_position_rows(account)
        latest_balance = await self._latest_paper_balance_snapshot(account)
        cash_balance = Decimal(str(latest_balance.cash_balance)) if latest_balance else _decimal((account.meta_json or {}).get("initial_cash"))
        if not positions:
            balance = await self._save_paper_balance_snapshot(
                account,
                cash_balance=cash_balance,
                market_value=Decimal("0"),
                total_asset=cash_balance,
                raw={"event": "paper_market_value_refresh", "positions": 0},
            )
            return {"balance": balance, "positions": []}

        engine = PaperTradingEngine()
        quotes = await engine.market_data.get_quotes([row.symbol for row in positions])
        refreshed: list[dict[str, Any]] = []
        for row in positions:
            quote = quotes.get(row.symbol)
            last_price = quote.last_price if quote else Decimal(str(row.last_price or row.cost_price or "0"))
            await self._upsert_paper_position_snapshot(
                account,
                symbol=row.symbol,
                quantity=int(row.quantity or 0),
                cost_price=Decimal(str(row.cost_price or "0")),
                last_price=last_price,
                raw={
                    "event": "paper_market_value_refresh",
                    "quote": self._quote_payload(quote) if quote else None,
                },
            )
        refreshed = await self.list_latest_positions(account)
        market_value = sum(_decimal(item.get("market_value")) for item in refreshed)
        balance = await self._save_paper_balance_snapshot(
            account,
            cash_balance=cash_balance,
            market_value=market_value,
            total_asset=cash_balance + market_value,
            raw={"event": "paper_market_value_refresh", "positions": len(refreshed)},
        )
        return {"balance": balance, "positions": refreshed}

    async def create_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        account = TradingAccount(
            account_code=_clean_text(payload.get("account_code")) or self._generate_account_code(payload),
            account_name=_clean_text(payload.get("account_name")) or "未命名账户",
            account_type=_normalize_account_type(payload.get("account_type")),
            broker_name=_clean_text(payload.get("broker_name")),
            broker_account_no=_clean_text(payload.get("broker_account_no")),
            shareholder_account=_clean_text(payload.get("shareholder_account")),
            exchange=_clean_text(payload.get("exchange")),
            status=_clean_text(payload.get("status")) or "active",
            is_default=1 if payload.get("is_default") else 0,
            meta_json=payload.get("meta_json") if isinstance(payload.get("meta_json"), dict) else None,
        )
        self.db.add(account)
        await self.db.flush()
        await self._save_binding(account, payload)
        if account.account_type == "paper":
            await self._apply_paper_initial_cash(account, payload, only_if_empty=True)
        if account.is_default:
            await self._unset_other_defaults(account.id)
        await self.db.flush()
        return await self.get_account_detail(account.id)

    async def update_account(self, account_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        account = await self.get_account(account_id)
        if account is None:
            raise LookupError("账户不存在")

        if "account_code" in payload:
            account.account_code = _clean_text(payload.get("account_code")) or account.account_code
        if "account_name" in payload:
            account.account_name = _clean_text(payload.get("account_name")) or account.account_name
        if "account_type" in payload:
            account.account_type = _normalize_account_type(payload.get("account_type"))
        if "broker_name" in payload:
            account.broker_name = _clean_text(payload.get("broker_name"))
        if "broker_account_no" in payload:
            account.broker_account_no = _clean_text(payload.get("broker_account_no"))
        if "shareholder_account" in payload:
            account.shareholder_account = _clean_text(payload.get("shareholder_account"))
        if "exchange" in payload:
            account.exchange = _clean_text(payload.get("exchange"))
        if "status" in payload:
            account.status = _clean_text(payload.get("status")) or account.status
        if "is_default" in payload:
            account.is_default = 1 if payload.get("is_default") else 0
        if "meta_json" in payload:
            account.meta_json = payload.get("meta_json") if isinstance(payload.get("meta_json"), dict) else None

        await self._save_binding(account, payload)
        if account.account_type == "paper" and "initial_cash" in payload:
            await self._apply_paper_initial_cash(account, payload, only_if_empty=False)
        if account.is_default:
            await self._unset_other_defaults(account.id)
        await self.db.flush()
        return await self.get_account_detail(account.id)

    async def archive_account(self, account_id: int) -> dict[str, Any]:
        account = await self.get_account(account_id)
        if account is None:
            raise LookupError("账户不存在")
        account.status = "archived"
        account.is_default = 0
        await self.db.flush()
        return await self.get_account_detail(account.id)

    async def set_default_account(self, account_id: int) -> dict[str, Any]:
        account = await self.get_account(account_id)
        if account is None:
            raise LookupError("账户不存在")
        account.is_default = 1
        await self._unset_other_defaults(account.id)
        await self.db.flush()
        return await self.get_account_detail(account.id)

    async def get_account_detail(self, account_id: int) -> dict[str, Any]:
        account_result = await self.db.execute(
            select(
                TradingAccount.id,
                TradingAccount.account_code,
                TradingAccount.account_name,
                TradingAccount.account_type,
                TradingAccount.broker_name,
                TradingAccount.broker_account_no,
                TradingAccount.shareholder_account,
                TradingAccount.exchange,
                TradingAccount.status,
                TradingAccount.is_default,
                TradingAccount.meta_json,
                TradingAccount.created_at,
                TradingAccount.updated_at,
            ).where(TradingAccount.id == account_id)
        )
        account = account_result.mappings().one()

        binding_result = await self.db.execute(
            select(
                AccountBinding.id,
                AccountBinding.binding_type,
                AccountBinding.client_path,
                AccountBinding.client_identity,
                AccountBinding.login_account_name,
                AccountBinding.login_account_mask,
                AccountBinding.is_active,
                AccountBinding.last_connected_at,
            ).where(AccountBinding.account_id == account_id)
        )
        bindings = binding_result.mappings().all()
        return self._serialize_account_mapping(account, bindings)

    async def _unset_other_defaults(self, account_id: int) -> None:
        result = await self.db.execute(select(TradingAccount).where(TradingAccount.id != account_id, TradingAccount.is_default == 1))
        for row in result.scalars().all():
            row.is_default = 0

    async def _get_account_bindings(self, account_id: int) -> list[AccountBinding]:
        result = await self.db.execute(select(AccountBinding).where(AccountBinding.account_id == account_id))
        return result.scalars().all()

    async def _save_binding(self, account: TradingAccount, payload: dict[str, Any]) -> None:
        binding_type = _clean_text(payload.get("binding_type")) or ("desktop" if account.account_type == "live" else "mock")
        client_identity = _clean_text(payload.get("client_identity")) or f"{binding_type}:{account.account_code}"
        result = await self.db.execute(
            select(AccountBinding).where(
                AccountBinding.account_id == account.id,
                AccountBinding.binding_type == binding_type,
                AccountBinding.client_identity == client_identity,
            )
        )
        binding = result.scalar_one_or_none()
        if binding is None:
            binding = AccountBinding(
                account_id=account.id,
                binding_type=binding_type,
                client_identity=client_identity,
                client_path=_clean_text(payload.get("client_path")),
                login_account_name=account.account_name,
                login_account_mask=account.broker_account_no,
                is_active=1,
                last_connected_at=_now() if payload.get("client_path") else None,
            )
            self.db.add(binding)
        else:
            if "client_path" in payload:
                binding.client_path = _clean_text(payload.get("client_path"))
            binding.login_account_name = account.account_name
            binding.login_account_mask = account.broker_account_no
            binding.is_active = 1 if payload.get("binding_active", True) else 0
            if payload.get("client_path"):
                binding.last_connected_at = _now()

    def _generate_account_code(self, payload: dict[str, Any]) -> str:
        account_type = _normalize_account_type(payload.get("account_type"))
        suffix = uuid4().hex[:8].upper()
        return f"{account_type.upper()}_{suffix}"

    async def _apply_paper_initial_cash(
        self,
        account: TradingAccount,
        payload: dict[str, Any],
        *,
        only_if_empty: bool,
    ) -> None:
        raw_initial_cash = payload.get("initial_cash")
        meta_json = dict(account.meta_json or {})
        if raw_initial_cash is None:
            raw_initial_cash = meta_json.get("initial_cash")
        initial_cash = _decimal(raw_initial_cash)
        if initial_cash <= 0:
            return
        meta_json["initial_cash"] = str(initial_cash)
        account.meta_json = meta_json
        if await self._has_paper_balance(account):
            return
        await self._save_paper_balance_snapshot(
            account,
            cash_balance=initial_cash,
            market_value=Decimal("0"),
            total_asset=initial_cash,
            raw={"event": "initial_cash", "initial_cash": str(initial_cash)},
        )

    async def _has_paper_balance(self, account: TradingAccount) -> bool:
        result = await self.db.execute(
            select(PaperBalanceSnapshot.id)
            .where(PaperBalanceSnapshot.account_id == account.id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _serialize_account(
        self,
        account: TradingAccount,
        bindings: list[AccountBinding],
        runtime: AccountRuntimeStatus | None = None,
    ) -> dict[str, Any]:
        return {
            "id": _loaded_value(account, "id"),
            "account_code": _loaded_value(account, "account_code"),
            "account_name": _loaded_value(account, "account_name"),
            "account_type": _loaded_value(account, "account_type"),
            "broker_name": _loaded_value(account, "broker_name"),
            "broker_account_no": _loaded_value(account, "broker_account_no"),
            "shareholder_account": _loaded_value(account, "shareholder_account"),
            "exchange": _loaded_value(account, "exchange"),
            "status": _loaded_value(account, "status"),
            "is_default": bool(_loaded_value(account, "is_default")),
            "meta_json": _loaded_value(account, "meta_json") or {},
            "created_at": _datetime_text(_loaded_value(account, "created_at")),
            "updated_at": _datetime_text(_loaded_value(account, "updated_at")),
            "bindings": [
                {
                    "id": _loaded_value(binding, "id"),
                    "binding_type": _loaded_value(binding, "binding_type"),
                    "client_path": _loaded_value(binding, "client_path"),
                    "client_identity": _loaded_value(binding, "client_identity"),
                    "login_account_name": _loaded_value(binding, "login_account_name"),
                    "login_account_mask": _loaded_value(binding, "login_account_mask"),
                    "is_active": bool(_loaded_value(binding, "is_active")),
                    "last_connected_at": _datetime_text(_loaded_value(binding, "last_connected_at")),
                }
                for binding in bindings
            ],
            "runtime_status": None
            if runtime is None
            else {
                "is_connected": bool(_loaded_value(runtime, "is_connected")),
                "is_ready": bool(_loaded_value(runtime, "is_ready")),
                "current_source": _loaded_value(runtime, "current_source"),
                "window_title": _loaded_value(runtime, "window_title"),
                "window_class": _loaded_value(runtime, "window_class"),
                "last_sync_at": _datetime_text(_loaded_value(runtime, "last_sync_at")),
                "last_heartbeat_at": _datetime_text(_loaded_value(runtime, "last_heartbeat_at")),
                "last_error_code": _loaded_value(runtime, "last_error_code"),
                "last_error_message": _loaded_value(runtime, "last_error_message"),
            },
        }

    def _serialize_account_mapping(self, account: Any, bindings: list[Any]) -> dict[str, Any]:
        return {
            "id": account["id"],
            "account_code": account["account_code"],
            "account_name": account["account_name"],
            "account_type": account["account_type"],
            "broker_name": account["broker_name"],
            "broker_account_no": account["broker_account_no"],
            "shareholder_account": account["shareholder_account"],
            "exchange": account["exchange"],
            "status": account["status"],
            "is_default": bool(account["is_default"]),
            "meta_json": account["meta_json"] or {},
            "created_at": _datetime_text(account["created_at"]),
            "updated_at": _datetime_text(account["updated_at"]),
            "bindings": [
                {
                    "id": binding["id"],
                    "binding_type": binding["binding_type"],
                    "client_path": binding["client_path"],
                    "client_identity": binding["client_identity"],
                    "login_account_name": binding["login_account_name"],
                    "login_account_mask": binding["login_account_mask"],
                    "is_active": bool(binding["is_active"]),
                    "last_connected_at": _datetime_text(binding["last_connected_at"]),
                }
                for binding in bindings
            ],
            "runtime_status": None,
        }

    async def ensure_account(self, account_info: dict[str, Any] | None = None) -> TradingAccount:
        info = account_info or {}
        account_type = _normalize_account_type(info.get("account_type"))
        code = _account_code(info)

        result = await self.db.execute(select(TradingAccount).where(TradingAccount.account_code == code))
        account = result.scalar_one_or_none()
        if account is None:
            account = TradingAccount(
                account_code=code,
                account_name=str(info.get("account_name") or code),
                account_type=account_type,
                broker_name="同花顺",
                broker_account_no=str(info.get("capital_account") or "") or None,
                shareholder_account=str(info.get("shareholder_account") or "") or None,
                exchange=str(info.get("market") or "") or None,
                status="active",
                is_default=1,
                meta_json={"source": "ths_desktop", "raw_account": info},
            )
            self.db.add(account)
            await self.db.flush()
        else:
            account.account_name = str(info.get("account_name") or account.account_name)
            account.account_type = account_type
            account.broker_account_no = str(info.get("capital_account") or account.broker_account_no or "") or None
            account.shareholder_account = str(info.get("shareholder_account") or account.shareholder_account or "") or None
            account.exchange = str(info.get("market") or account.exchange or "") or None
            account.meta_json = {"source": "ths_desktop", "raw_account": info}

        await self._upsert_binding(account, info)
        return account

    async def _upsert_binding(self, account: TradingAccount, account_info: dict[str, Any]) -> None:
        identity = f"ths:{account.account_code}"
        result = await self.db.execute(
            select(AccountBinding).where(
                AccountBinding.account_id == account.id,
                AccountBinding.binding_type == "desktop",
                AccountBinding.client_identity == identity,
            )
        )
        binding = result.scalar_one_or_none()
        if binding is None:
            binding = AccountBinding(
                account_id=account.id,
                binding_type="desktop",
                client_identity=identity,
                login_account_name=account.account_name,
                login_account_mask=account.broker_account_no,
                is_active=1,
                last_connected_at=_now(),
            )
            self.db.add(binding)
        else:
            binding.login_account_name = account.account_name
            binding.login_account_mask = account.broker_account_no
            binding.last_connected_at = _now()

    async def update_runtime_status(
        self,
        account: TradingAccount,
        status_data: dict[str, Any] | None,
        *,
        last_error: Exception | None = None,
    ) -> None:
        result = await self.db.execute(
            select(AccountRuntimeStatus).where(AccountRuntimeStatus.account_id == account.id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = AccountRuntimeStatus(account_id=account.id)
            self.db.add(row)

        status_data = status_data or {}
        row.is_connected = 1 if status_data.get("connected", True) else 0
        row.is_ready = 1 if status_data.get("ready", True) else 0
        row.current_source = account.account_type
        row.window_title = status_data.get("window_title")
        row.window_class = status_data.get("window_class")
        row.last_heartbeat_at = _now()
        row.detail_json = {"status": status_data}
        if last_error:
            row.last_error_code = type(last_error).__name__
            row.last_error_message = str(last_error)[:255]
        else:
            row.last_error_code = None
            row.last_error_message = None

    async def create_task(
        self,
        account: TradingAccount,
        operation_type: str,
        request_json: dict[str, Any] | None = None,
    ) -> AccountOperationTask:
        task = AccountOperationTask(
            task_no=f"YJX-{_now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}",
            account_id=account.id,
            account_type=account.account_type,
            operation_type=operation_type,
            request_json=request_json,
            status="running",
            started_at=_now(),
        )
        self.db.add(task)
        await self.db.flush()
        return task

    async def finish_task(
        self,
        task: AccountOperationTask,
        status: str,
        response_json: Any = None,
        error: Exception | None = None,
    ) -> None:
        task.status = status
        task.response_json = response_json if isinstance(response_json, dict) else {"result": response_json}
        task.finished_at = _now()
        if error:
            task.error_code = type(error).__name__
            task.error_message = str(error)[:255]

    async def append_task_step(
        self,
        task: AccountOperationTask,
        step_name: str,
        status: str,
        input_json: dict[str, Any] | None = None,
        output_json: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        result = await self.db.execute(
            select(AccountOperationStep.step_index)
            .where(AccountOperationStep.task_id == task.id)
            .order_by(AccountOperationStep.step_index.desc())
            .limit(1)
        )
        last_index = result.scalar_one_or_none() or 0
        now = _now()
        self.db.add(
            AccountOperationStep(
                task_id=task.id,
                step_index=last_index + 1,
                step_name=step_name,
                status=status,
                input_json=input_json,
                output_json=output_json,
                error_message=error_message[:255] if error_message else None,
                started_at=now,
                finished_at=now,
            )
        )

    async def save_balance(self, account: TradingAccount, data: dict[str, Any]) -> None:
        if not data or data.get("error"):
            return
        snapshot_cls = LiveBalanceSnapshot if account.account_type == "live" else PaperBalanceSnapshot if account.account_type == "paper" else None
        if snapshot_cls is None:
            return
        now = _now()
        self.db.add(
            snapshot_cls(
                account_id=account.id,
                trade_date=_today(),
                snapshot_time=now,
                total_asset=_decimal(data.get("total_asset")),
                cash_balance=_decimal(data.get("cash_balance")),
                available_cash=_decimal(data.get("available_cash")),
                withdrawable_cash=_decimal(data.get("withdrawable_cash")),
                frozen_cash=_decimal(data.get("frozen_cash")),
                market_value=_decimal(data.get("market_value")),
                realized_pnl=_decimal(data.get("realized_pnl")) if data.get("realized_pnl") is not None else None,
                unrealized_pnl=_decimal(data.get("unrealized_pnl")) if data.get("unrealized_pnl") is not None else None,
                source=account.account_type,
                raw_json=data.get("raw") or data,
            )
        )

    async def save_positions(self, account: TradingAccount, rows: list[dict[str, Any]]) -> None:
        snapshot_cls = LivePositionSnapshot if account.account_type == "live" else PaperPositionSnapshot if account.account_type == "paper" else None
        if snapshot_cls is None:
            return
        now = _now()
        for item in rows:
            symbol = str(item.get("symbol") or "").strip()
            if not symbol:
                continue
            self.db.add(
                snapshot_cls(
                    account_id=account.id,
                    trade_date=_today(),
                    snapshot_time=now,
                    symbol=symbol,
                    name=item.get("name") or None,
                    exchange=item.get("exchange") or None,
                    quantity=_int(item.get("quantity")),
                    available_quantity=_int(item.get("available_quantity")),
                    frozen_quantity=_int(item.get("frozen_quantity")),
                    cost_price=_decimal(item.get("cost_price")),
                    last_price=_decimal(item.get("last_price")),
                    market_value=_decimal(item.get("market_value")),
                    unrealized_pnl=_decimal(item.get("unrealized_pnl")),
                    pnl_ratio=_decimal(item.get("pnl_ratio")) if item.get("pnl_ratio") is not None else None,
                    source=account.account_type,
                    raw_json=item.get("raw") or item,
                )
            )

    async def save_orders(self, account: TradingAccount, rows: list[dict[str, Any]]) -> None:
        if account.account_type not in {"live", "paper"}:
            return
        for item in rows:
            await self._upsert_order(account, item)

    async def save_trades(self, account: TradingAccount, rows: list[dict[str, Any]]) -> None:
        if account.account_type not in {"live", "paper"}:
            return
        for item in rows:
            await self._upsert_trade(account, item)

    async def save_place_order_result(self, account: TradingAccount, result: dict[str, Any]) -> None:
        request = result.get("request") or {}
        entrust_no = result.get("entrust_no") or (result.get("action_result") or {}).get("entrust_no")
        matched_orders = result.get("matched_orders") or []
        if matched_orders:
            for row in matched_orders:
                normalized = {
                    "broker_order_id": row.get("合同编号") or row.get("委托编号") or entrust_no,
                    "symbol": row.get("证券代码") or request.get("symbol"),
                    "name": row.get("证券名称"),
                    "side": request.get("side"),
                    "price": row.get("委托价格") or request.get("price"),
                    "quantity": row.get("委托数量") or request.get("quantity"),
                    "filled_quantity": row.get("成交数量"),
                    "avg_fill_price": row.get("成交均价"),
                    "status": row.get("委托状态") or result.get("status"),
                    "raw": row,
                }
                await self._upsert_order(account, normalized)
            return

        await self._upsert_order(
            account,
            {
                "broker_order_id": entrust_no,
                "order_id": entrust_no or uuid4().hex,
                "symbol": request.get("symbol"),
                "side": request.get("side"),
                "price": request.get("price"),
                "quantity": request.get("quantity"),
                "filled_quantity": 0,
                "status": result.get("status"),
                "raw": result,
            },
        )

    async def save_cancel_result(self, account: TradingAccount, entrust_no: str, result: dict[str, Any]) -> None:
        order = await self._find_order(account, entrust_no)
        if order is not None:
            from_status = order.status
            order.status = "cancel_pending" if result.get("status") == "submitted" else _normalize_order_status(result.get("status"))
            order.canceled_at = _now()
            await self._append_order_status_log(
                account=account,
                order=order,
                from_status=from_status,
                to_status=order.status,
                event_type="cancel_request",
                event_source="ths_desktop",
                detail=result,
                message=result.get("message") or "撤单流程已提交",
            )

    async def save_order_confirmation(
        self,
        account: TradingAccount,
        confirmation: dict[str, Any],
        *,
        event_type: str = "sync_update",
        event_message: str = "订单确认回查完成",
    ) -> None:
        if account.account_type not in {"live", "paper"}:
            return
        matched_orders = confirmation.get("matched_orders") or []
        matched_trades = confirmation.get("matched_trades") or []
        for item in matched_orders:
            order = await self._upsert_order(account, item)
            await self._append_confirmation_status(account, order, confirmation, event_type, event_message)
        for item in matched_trades:
            await self._upsert_trade(account, item)

    async def _append_confirmation_status(
        self,
        account: TradingAccount,
        order: LiveOrder | PaperOrder,
        confirmation: dict[str, Any],
        event_type: str,
        event_message: str,
    ) -> None:
        final_status = _normalize_order_status(confirmation.get("final_status"))
        if final_status in {"unconfirmed", "confirmation_failed"}:
            final_status = order.status
        if order.status != final_status:
            from_status = order.status
            order.status = final_status
            await self._append_order_status_log(
                account=account,
                order=order,
                from_status=from_status,
                to_status=final_status,
                event_type=event_type,
                event_source="ths_desktop",
                detail=confirmation,
                message=event_message,
            )
            return
        await self._append_order_status_log(
            account=account,
            order=order,
            from_status=order.status,
            to_status=order.status,
            event_type=event_type,
            event_source="ths_desktop",
            detail=confirmation,
            message=event_message,
        )

    def _order_cls(self, account: TradingAccount) -> type[LiveOrder] | type[PaperOrder] | type[BacktestOrder]:
        if account.account_type == "live":
            return LiveOrder
        if account.account_type == "backtest":
            return BacktestOrder
        return PaperOrder

    def _trade_cls(self, account: TradingAccount) -> type[LiveTrade] | type[PaperTrade] | type[BacktestTrade]:
        if account.account_type == "live":
            return LiveTrade
        if account.account_type == "backtest":
            return BacktestTrade
        return PaperTrade

    def _order_status_cls(self, account: TradingAccount) -> type[LiveOrderStatusLog] | type[PaperOrderStatusLog]:
        return LiveOrderStatusLog if account.account_type == "live" else PaperOrderStatusLog

    async def _find_order(self, account: TradingAccount, broker_order_no: str | None) -> LiveOrder | PaperOrder | None:
        if not broker_order_no:
            return None
        order_cls = self._order_cls(account)
        result = await self.db.execute(
            select(order_cls).where(
                order_cls.account_id == account.id,
                order_cls.broker_order_no == broker_order_no,
            )
        )
        return result.scalar_one_or_none()

    async def _upsert_order(self, account: TradingAccount, item: dict[str, Any]) -> LiveOrder | PaperOrder:
        order_cls = self._order_cls(account)
        broker_order_no = str(item.get("broker_order_id") or item.get("broker_order_no") or "").strip() or None
        order_no = str(item.get("order_id") or item.get("order_no") or broker_order_no or uuid4().hex).strip()
        order = await self._find_order(account, broker_order_no)
        if order is None:
            result = await self.db.execute(select(order_cls).where(order_cls.order_no == order_no))
            order = result.scalar_one_or_none()

        trade_date = _today()
        submitted_at = _parse_datetime(item.get("submitted_at"), trade_date)
        status = _normalize_order_status(item.get("status"))
        if order is None:
            order = order_cls(
                account_id=account.id,
                order_no=order_no,
                broker_order_no=broker_order_no,
                trade_date=trade_date,
                symbol=str(item.get("symbol") or "").strip(),
                name=item.get("name") or None,
                side=str(item.get("side") or ""),
                price=_decimal(item.get("price")),
                quantity=_int(item.get("quantity")),
                filled_quantity=_int(item.get("filled_quantity")),
                canceled_quantity=_int(item.get("canceled_quantity")),
                avg_fill_price=_decimal(item.get("avg_fill_price")),
                status=status,
                source=account.account_type,
                submitted_at=submitted_at,
                raw_json=item.get("raw") or item,
            )
            self.db.add(order)
            await self.db.flush()
            await self._append_order_status_log(account, order, None, status, "sync_update", "ths_desktop", item)
        else:
            from_status = order.status
            order.broker_order_no = broker_order_no or order.broker_order_no
            order.symbol = str(item.get("symbol") or order.symbol or "").strip()
            order.name = item.get("name") or order.name
            order.side = str(item.get("side") or order.side or "")
            order.price = _decimal(item.get("price"))
            order.quantity = _int(item.get("quantity"))
            order.filled_quantity = _int(item.get("filled_quantity"))
            order.canceled_quantity = _int(item.get("canceled_quantity"))
            order.avg_fill_price = _decimal(item.get("avg_fill_price"))
            order.status = status
            order.submitted_at = submitted_at or order.submitted_at
            order.raw_json = item.get("raw") or item
            if from_status != status:
                await self._append_order_status_log(account, order, from_status, status, "sync_update", "ths_desktop", item)
        return order

    async def _upsert_trade(self, account: TradingAccount, item: dict[str, Any]) -> LiveTrade | PaperTrade | None:
        trade_cls = self._trade_cls(account)
        trade_id = str(item.get("trade_id") or item.get("broker_trade_id") or "").strip()
        if not trade_id:
            return None
        result = await self.db.execute(select(trade_cls).where(trade_cls.trade_id == trade_id))
        trade = result.scalar_one_or_none()
        trade_date = _today()
        traded_at = _parse_datetime(item.get("traded_at"), trade_date) or _now()
        broker_order_no = str(item.get("order_id") or item.get("broker_order_no") or "").strip() or None
        order = await self._find_order(account, broker_order_no)
        if trade is None:
            trade = trade_cls(
                account_id=account.id,
                order_id=order.id if order else None,
                trade_id=trade_id,
                broker_trade_no=str(item.get("broker_trade_id") or trade_id),
                broker_order_no=broker_order_no,
                trade_date=trade_date,
                traded_at=traded_at,
                symbol=str(item.get("symbol") or "").strip(),
                name=item.get("name") or None,
                side=str(item.get("side") or ""),
                price=_decimal(item.get("price")),
                quantity=_int(item.get("quantity")),
                amount=_decimal(item.get("amount")),
                commission=_decimal(item.get("commission")),
                stamp_tax=_decimal(item.get("stamp_tax")),
                raw_json=item.get("raw") or item,
            )
            self.db.add(trade)
        else:
            trade.order_id = order.id if order else trade.order_id
            trade.broker_order_no = broker_order_no or trade.broker_order_no
            trade.traded_at = traded_at
            trade.symbol = str(item.get("symbol") or trade.symbol or "").strip()
            trade.name = item.get("name") or trade.name
            trade.side = str(item.get("side") or trade.side or "")
            trade.price = _decimal(item.get("price"))
            trade.quantity = _int(item.get("quantity"))
            trade.amount = _decimal(item.get("amount"))
            trade.commission = _decimal(item.get("commission"))
            trade.stamp_tax = _decimal(item.get("stamp_tax"))
            trade.raw_json = item.get("raw") or item
        return trade

    async def _append_order_status_log(
        self,
        account: TradingAccount,
        order: LiveOrder | PaperOrder,
        from_status: str | None,
        to_status: str,
        event_type: str,
        event_source: str,
        detail: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        self.db.add(
            self._order_status_cls(account)(
                account_id=account.id,
                order_id=order.id,
                broker_order_no=order.broker_order_no,
                from_status=from_status,
                to_status=to_status,
                event_type=event_type,
                event_source=event_source,
                event_time=_now(),
                detail_json=detail,
                message=message,
            )
        )

    async def place_paper_order(
        self,
        account: TradingAccount,
        *,
        side: str,
        symbol: str,
        price: Decimal,
        quantity: int,
        idempotency_key: str | None = None,
        remark: str | None = None,
    ) -> dict[str, Any]:
        if account.account_type != "paper":
            raise ValueError("当前账户不是模拟账户")
        if side not in {"buy", "sell"}:
            raise ValueError("模拟下单方向必须是 buy 或 sell")
        if price <= 0 or quantity <= 0:
            raise ValueError("模拟下单价格和数量必须大于 0")

        now = _now()
        trade_date = _today()
        latest_balance = await self._latest_paper_balance_snapshot(account)
        cash_balance = Decimal(str(latest_balance.cash_balance)) if latest_balance else _decimal((account.meta_json or {}).get("initial_cash"))
        current_position = await self._latest_paper_position_snapshot(account, symbol)
        current_quantity = int(current_position.quantity or 0) if current_position else 0
        current_cost_price = Decimal(str(current_position.cost_price or "0")) if current_position else Decimal("0")
        decision = await PaperTradingEngine().match_order(
            PaperOrderRequest(symbol=symbol, side=side, price=price, quantity=quantity),  # type: ignore[arg-type]
            available_cash=cash_balance,
            available_quantity=current_quantity,
        )

        order_no = f"PORD-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        broker_order_no = f"PMOCK-{uuid4().hex[:12].upper()}"
        order = PaperOrder(
            account_id=account.id,
            idempotency_key=idempotency_key,
            order_no=order_no,
            broker_order_no=broker_order_no,
            trade_date=trade_date,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            filled_quantity=decision.fill_quantity,
            canceled_quantity=0,
            avg_fill_price=decision.fill_price if decision.fill_quantity else None,
            status=decision.status,
            remark=remark,
            source="paper",
            submitted_at=now,
            accepted_at=now if decision.status != "rejected" else None,
            rejected_at=now if decision.status == "rejected" else None,
            raw_json={
                "engine": "paper_trading_engine",
                "idempotency_key": idempotency_key,
                "remark": remark,
                "match": self._decision_payload(decision),
            },
        )
        self.db.add(order)
        await self.db.flush()

        trade: PaperTrade | None = None
        balance = await self.get_latest_balance(account)
        if decision.is_filled:
            trade_no = f"PTRD-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
            trade = PaperTrade(
                account_id=account.id,
                order_id=order.id,
                trade_id=trade_no,
                broker_trade_no=trade_no,
                broker_order_no=broker_order_no,
                trade_date=trade_date,
                traded_at=now,
                symbol=symbol,
                side=side,
                price=decision.fill_price,
                quantity=decision.fill_quantity,
                amount=decision.amount,
                commission=decision.commission,
                stamp_tax=decision.stamp_tax,
                transfer_fee=decision.transfer_fee,
                raw_json={"engine": "paper_trading_engine", "quote": self._quote_payload(decision.quote)},
            )
            self.db.add(trade)

            if side == "buy":
                new_quantity = current_quantity + decision.fill_quantity
                new_cash = cash_balance - decision.amount - decision.total_fee
                previous_cost = current_cost_price * Decimal(current_quantity)
                new_cost_price = (previous_cost + decision.amount + decision.total_fee) / Decimal(new_quantity)
            else:
                new_quantity = current_quantity - decision.fill_quantity
                new_cash = cash_balance + decision.amount - decision.total_fee
                new_cost_price = current_cost_price if new_quantity > 0 else Decimal("0")

            await self._upsert_paper_position_snapshot(
                account,
                symbol=symbol,
                quantity=new_quantity,
                cost_price=new_cost_price,
                last_price=decision.market_value_price,
                raw={
                    "event": "paper_engine_fill",
                    "side": side,
                    "fill_price": str(decision.fill_price),
                    "fill_quantity": decision.fill_quantity,
                    "order_no": order_no,
                    "trade_id": trade_no,
                    "quote": self._quote_payload(decision.quote),
                },
            )
            positions = await self.list_latest_positions(account)
            market_value = sum(_decimal(item.get("market_value")) for item in positions)
            balance = await self._save_paper_balance_snapshot(
                account,
                cash_balance=new_cash,
                market_value=market_value,
                total_asset=new_cash + market_value,
                raw={
                    "event": "paper_engine_fill",
                    "side": side,
                    "amount": str(decision.amount),
                    "total_fee": str(decision.total_fee),
                    "order_no": order_no,
                    "trade_id": trade_no,
                },
            )
        await self._append_order_status_log(
            account,
            order,
            None,
            decision.status,
            "fill" if decision.is_filled else decision.status,
            "paper_engine",
            {"order_no": order_no, "match": self._decision_payload(decision)},
            decision.reason,
        )
        await self.db.flush()
        return {
            "status": decision.status,
            "reason": decision.reason,
            "order": self._serialize_order(order),
            "trade": self._serialize_trade(trade) if trade else None,
            "balance": balance,
            "positions": await self.list_latest_positions(account),
        }

    async def _latest_paper_balance_snapshot(self, account: TradingAccount) -> PaperBalanceSnapshot | None:
        result = await self.db.execute(
            select(PaperBalanceSnapshot)
            .where(PaperBalanceSnapshot.account_id == account.id)
            .order_by(PaperBalanceSnapshot.snapshot_time.desc(), PaperBalanceSnapshot.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _latest_paper_position_snapshot(self, account: TradingAccount, symbol: str) -> PaperPositionSnapshot | None:
        result = await self.db.execute(
            select(PaperPositionSnapshot)
            .where(PaperPositionSnapshot.account_id == account.id, PaperPositionSnapshot.symbol == symbol)
            .order_by(PaperPositionSnapshot.snapshot_time.desc(), PaperPositionSnapshot.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _latest_paper_position_rows(self, account: TradingAccount) -> list[PaperPositionSnapshot]:
        result = await self.db.execute(
            select(PaperPositionSnapshot)
            .where(PaperPositionSnapshot.account_id == account.id)
            .order_by(PaperPositionSnapshot.snapshot_time.desc(), PaperPositionSnapshot.id.desc())
        )
        latest_by_symbol: dict[str, PaperPositionSnapshot] = {}
        for row in result.scalars().all():
            if row.symbol not in latest_by_symbol and int(row.quantity or 0) > 0:
                latest_by_symbol[row.symbol] = row
        return list(latest_by_symbol.values())

    async def _upsert_paper_position_snapshot(
        self,
        account: TradingAccount,
        *,
        symbol: str,
        quantity: int,
        cost_price: Decimal,
        last_price: Decimal,
        raw: dict[str, Any],
    ) -> PaperPositionSnapshot:
        now = _now()
        market_value = last_price * Decimal(quantity)
        result = await self.db.execute(
            select(PaperPositionSnapshot).where(
                PaperPositionSnapshot.account_id == account.id,
                PaperPositionSnapshot.trade_date == _today(),
                PaperPositionSnapshot.symbol == symbol,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = PaperPositionSnapshot(
                account_id=account.id,
                trade_date=_today(),
                snapshot_time=now,
                symbol=symbol,
                quantity=quantity,
                available_quantity=quantity,
                frozen_quantity=0,
                cost_price=cost_price,
                last_price=last_price,
                market_value=market_value,
                unrealized_pnl=(last_price - cost_price) * Decimal(quantity),
                pnl_ratio=((last_price - cost_price) / cost_price) if cost_price > 0 else None,
                source="paper",
                raw_json=raw,
            )
            self.db.add(row)
        else:
            row.snapshot_time = now
            row.quantity = quantity
            row.available_quantity = quantity
            row.frozen_quantity = 0
            row.cost_price = cost_price
            row.last_price = last_price
            row.market_value = market_value
            row.unrealized_pnl = (last_price - cost_price) * Decimal(quantity)
            row.pnl_ratio = ((last_price - cost_price) / cost_price) if cost_price > 0 else None
            row.raw_json = raw
        return row

    async def _save_paper_balance_snapshot(
        self,
        account: TradingAccount,
        *,
        cash_balance: Decimal,
        market_value: Decimal,
        total_asset: Decimal,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        now = _now()
        row = PaperBalanceSnapshot(
            account_id=account.id,
            trade_date=_today(),
            snapshot_time=now,
            total_asset=total_asset,
            cash_balance=cash_balance,
            available_cash=cash_balance,
            withdrawable_cash=cash_balance,
            frozen_cash=Decimal("0"),
            market_value=market_value,
            realized_pnl=None,
            unrealized_pnl=None,
            source="paper",
            raw_json=raw,
        )
        self.db.add(row)
        await self.db.flush()
        return self._serialize_balance(row)

    def _balance_payload(
        self,
        cash_balance: Decimal,
        market_value: Decimal,
        total_asset: Decimal,
        updated_at: datetime | None = None,
    ) -> dict[str, Any]:
        return {
            "account_id": "paper-local",
            "mode": "paper",
            "total_asset": str(total_asset),
            "available_cash": str(cash_balance),
            "withdrawable_cash": str(cash_balance),
            "market_value": str(market_value),
            "cash_balance": str(cash_balance),
            "frozen_cash": "0",
            "updated_at": updated_at.isoformat(sep=" ", timespec="seconds") if updated_at else "",
        }

    def _serialize_balance(self, row: PaperBalanceSnapshot | LiveBalanceSnapshot) -> dict[str, Any]:
        return {
            "account_id": str(row.account_id),
            "mode": row.source,
            "total_asset": str(row.total_asset),
            "available_cash": str(row.available_cash),
            "withdrawable_cash": str(row.withdrawable_cash),
            "market_value": str(row.market_value),
            "cash_balance": str(row.cash_balance),
            "frozen_cash": str(row.frozen_cash),
            "updated_at": row.snapshot_time.isoformat(sep=" ", timespec="seconds") if row.snapshot_time else "",
        }

    def _serialize_position(self, row: PaperPositionSnapshot | LivePositionSnapshot) -> dict[str, Any]:
        return {
            "position_id": f"{row.account_id}:{row.symbol}",
            "symbol": row.symbol,
            "name": row.name or "",
            "quantity": int(row.quantity or 0),
            "available_quantity": int(row.available_quantity or 0),
            "cost_price": str(row.cost_price or "0"),
            "last_price": str(row.last_price or "0"),
            "market_value": str(row.market_value or "0"),
            "unrealized_pnl": str(row.unrealized_pnl or "0"),
        }

    def _quote_payload(self, quote: Any) -> dict[str, Any] | None:
        if quote is None:
            return None
        return {
            "symbol": quote.symbol,
            "name": quote.name,
            "exchange": quote.exchange,
            "last_price": str(quote.last_price),
            "limit_up": str(quote.limit_up) if quote.limit_up is not None else None,
            "limit_down": str(quote.limit_down) if quote.limit_down is not None else None,
            "volume": quote.volume,
            "trading_status": quote.trading_status,
            "timestamp": quote.timestamp.isoformat(sep=" ", timespec="seconds"),
        }

    def _decision_payload(self, decision: Any) -> dict[str, Any]:
        return {
            "status": decision.status,
            "fill_price": str(decision.fill_price),
            "fill_quantity": decision.fill_quantity,
            "requested_quantity": decision.requested_quantity,
            "amount": str(decision.amount),
            "commission": str(decision.commission),
            "stamp_tax": str(decision.stamp_tax),
            "transfer_fee": str(decision.transfer_fee),
            "total_fee": str(decision.total_fee),
            "reason": decision.reason,
            "quote": self._quote_payload(decision.quote),
        }

    def _serialize_order(self, row: LiveOrder | PaperOrder | BacktestOrder) -> dict[str, Any]:
        return {
            "order_id": row.order_no or str(row.id),
            "broker_order_id": row.broker_order_no or "",
            "symbol": row.symbol,
            "name": row.name or "",
            "side": row.side,
            "price": str(row.price),
            "quantity": int(row.quantity or 0),
            "filled_quantity": int(row.filled_quantity or 0),
            "avg_fill_price": str(row.avg_fill_price or "0"),
            "status": row.status,
            "submitted_at": row.submitted_at.isoformat(sep=" ", timespec="seconds") if row.submitted_at else "",
        }

    def _serialize_trade(self, row: LiveTrade | PaperTrade | BacktestTrade) -> dict[str, Any]:
        return {
            "trade_id": row.trade_id or str(row.id),
            "broker_trade_id": row.broker_trade_no or "",
            "order_id": row.broker_order_no or str(row.order_id or ""),
            "symbol": row.symbol,
            "name": row.name or "",
            "side": row.side,
            "price": str(row.price),
            "quantity": int(row.quantity or 0),
            "amount": str(row.amount),
            "traded_at": row.traded_at.isoformat(sep=" ", timespec="seconds") if row.traded_at else "",
        }
