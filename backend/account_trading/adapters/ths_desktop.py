from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import pywinauto
import pywinauto.clipboard
import pywinauto.keyboard
import win32con
import win32gui
import win32process
from pywinauto import Application, Desktop
from pywinauto.application import ProcessNotFoundError
from pywinauto.findwindows import ElementNotFoundError


OrderSide = Literal["buy", "sell"]


class CaptchaRequiredError(RuntimeError):
    def __init__(self, message: str = "检测到验证码弹窗，请在同花顺中人工处理后继续。") -> None:
        super().__init__(message)


class TradingClientNotReadyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ThsOrderRequest:
    symbol: str
    side: OrderSide
    price: Decimal
    quantity: int


class ThsDesktopAdapter:
    """同花顺桌面自动化适配器，不依赖 easytrader。

    已根据本机实测行为实现：
    - 使用 pywinauto 连接或启动 xiadan.exe。
    - 使用 TreeView 菜单切换功能页。
    - 使用 WM_CHAR 填写买入/卖出表单。
    - 自行处理委托确认、提示、撤单确认等弹窗。
    - 读取余额使用控件 ID。
    - 表格读取使用 Ctrl+A/C 复制，不做验证码自动识别。
    - 撤单支持直接点击撤单页按钮，绕开原 easytrader 的 OCR 依赖。
    """

    LEFT_MENU_CONTROL_ID = 129
    COMMON_GRID_CONTROL_ID = 1047
    TRADE_SECURITY_CONTROL_ID = 1032
    TRADE_PRICE_CONTROL_ID = 1033
    TRADE_AMOUNT_CONTROL_ID = 1034
    TRADE_SUBMIT_CONTROL_ID = 1006
    POP_DIALOG_TITLE_CONTROL_ID = 1365

    BALANCE_CONTROL_IDS = {
        "资金余额": 1012,
        "可用金额": 1016,
        "可取金额": 1017,
        "股票市值": 1014,
        "总资产": 1015,
    }

    GRID_DTYPE = {
        "操作日期": str,
        "委托编号": str,
        "申请编号": str,
        "合同编号": str,
        "证券代码": str,
        "股东代码": str,
        "资金帐号": str,
        "资金帐户": str,
        "发生日期": str,
    }
    def __init__(
        self,
        client_path: str | Path,
        captcha_code: str | None = None,
        wait_manual_captcha: bool = False,
        manual_captcha_timeout: int = 120,
    ) -> None:
        self.client_path = Path(client_path)
        self.captcha_code = captcha_code
        self.wait_manual_captcha = wait_manual_captcha
        self.manual_captcha_timeout = manual_captcha_timeout
        self.app: Application | None = None
        self.main: Any | None = None

    def connect(self) -> None:
        if not self.client_path.exists():
            raise FileNotFoundError(f"同花顺交易客户端不存在: {self.client_path}")

        self.app = Application(backend="win32")
        try:
            self.app.connect(path=str(self.client_path), timeout=5)
        except ProcessNotFoundError:
            self.app = Application(backend="win32").start(str(self.client_path))
        except Exception:
            self.app = Application(backend="win32").start(str(self.client_path))

        self.main = self._wait_for_main_window(timeout_seconds=30)

    def ensure_connected(self) -> tuple[Application, Any]:
        if self.app is None or self.main is None:
            self.connect()
        assert self.app is not None
        assert self.main is not None
        return self.app, self.main

    def _find_main_window(self):
        assert self.app is not None
        process_id = self.app.process
        for window in Desktop(backend="win32").windows():
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(window.handle)
            except Exception:
                continue
            if window_pid != process_id:
                continue
            if "网上股票交易系统" in (window.window_text() or ""):
                return self.app.window(handle=window.handle)
        return self.app.top_window()

    def _wait_for_main_window(self, timeout_seconds: int):
        start = time.monotonic()
        last_error: Exception | None = None
        while time.monotonic() - start <= timeout_seconds:
            try:
                main = self._find_main_window()
                if main.exists(timeout=1):
                    try:
                        main.wait("visible", timeout=2)
                    except Exception:
                        pass
                    return main
            except Exception as exc:
                last_error = exc
            time.sleep(0.8)
        raise TradingClientNotReadyError(
            f"同花顺交易客户端已尝试启动，但 {timeout_seconds} 秒内未发现主窗口。"
        ) from last_error

    def status(self) -> dict[str, Any]:
        _, main = self.ensure_connected()
        return {
            "connected": True,
            "ready": self._is_trade_page_ready(),
            "window_title": main.window_text(),
            "window_class": main.class_name(),
            "window_rect": str(main.rectangle()),
            "account": self.get_account_info(),
        }

    def get_account_info(self) -> dict[str, Any]:
        _, main = self.ensure_connected()
        texts: list[dict[str, Any]] = []
        for child in main.children():
            try:
                text = (child.window_text() or "").strip()
                if not text:
                    continue
                texts.append(
                    {
                        "control_id": child.control_id(),
                        "class_name": child.class_name(),
                        "text": text,
                    }
                )
            except Exception:
                continue

        account_name = self._first_control_text(texts, [2322, 2380])
        market = self._first_control_text(texts, [1003])
        shareholder_account = self._first_control_text(texts, [1004])
        capital_account = self._first_control_text(texts, [1711])

        account_text = " ".join(item["text"] for item in texts)
        is_paper = "模拟" in account_text
        is_live = bool(capital_account) and not is_paper

        return {
            "account_name": account_name,
            "account_type": "paper" if is_paper else "live" if is_live else "unknown",
            "account_type_label": "模拟盘" if is_paper else "实盘" if is_live else "未知",
            "market": market,
            "shareholder_account": shareholder_account,
            "capital_account": capital_account,
            "raw_controls": [
                item
                for item in texts
                if item["control_id"] in (1003, 1004, 1711, 2322, 2380)
                or "账户" in item["text"]
                or "帐户" in item["text"]
                or "模拟" in item["text"]
            ],
        }

    def _first_control_text(self, controls: list[dict[str, Any]], control_ids: list[int]) -> str:
        for control_id in control_ids:
            for item in controls:
                if item["control_id"] == control_id and item["text"]:
                    return str(item["text"])
        return ""

    def get_balance(self) -> dict[str, float]:
        _, main = self.ensure_connected()
        self.switch_menu(["查询[F4]", "资金股票"])
        self._assert_trade_page_ready()
        result: dict[str, float] = {}
        for key, control_id in self.BALANCE_CONTROL_IDS.items():
            try:
                result[key] = float(
                    main.child_window(
                        control_id=control_id,
                        class_name="Static",
                    ).window_text()
                )
            except ElementNotFoundError as exc:
                raise TradingClientNotReadyError(
                    "未找到资金余额控件，通常表示同花顺交易端尚未登录、连接已断开，"
                    "或当前未进入“查询-资金股票”页面。"
                ) from exc
        return result

    def get_positions(self) -> list[dict[str, Any]]:
        self.switch_menu(["查询[F4]", "资金股票"])
        return self.read_grid()

    def get_today_orders(self) -> list[dict[str, Any]]:
        self.switch_menu(["查询[F4]", "当日委托"])
        return self.read_grid()

    def get_today_trades(self) -> list[dict[str, Any]]:
        self.switch_menu(["查询[F4]", "当日成交"])
        return self.read_grid()

    def get_history_orders(self) -> list[dict[str, Any]]:
        self.switch_menu(["查询[F4]", "历史委托"])
        return self.read_grid()

    def get_history_trades(self) -> list[dict[str, Any]]:
        self.switch_menu(["查询[F4]", "历史成交"])
        return self.read_grid()

    def buy(self, symbol: str, price: str | float | Decimal, quantity: int) -> dict[str, Any]:
        return self.place_order(
            ThsOrderRequest(
                symbol=symbol,
                side="buy",
                price=Decimal(str(price)),
                quantity=quantity,
            )
        )

    def sell(self, symbol: str, price: str | float | Decimal, quantity: int) -> dict[str, Any]:
        return self.place_order(
            ThsOrderRequest(
                symbol=symbol,
                side="sell",
                price=Decimal(str(price)),
                quantity=quantity,
            )
        )

    def place_order(self, request: ThsOrderRequest) -> dict[str, Any]:
        self.switch_menu(["买入[F1]"] if request.side == "buy" else ["卖出[F2]"])
        self.fill_trade_form(request)
        _, main = self.ensure_connected()
        main.child_window(
            control_id=self.TRADE_SUBMIT_CONTROL_ID,
            class_name="Button",
        ).wrapper_object().click()
        time.sleep(0.8)

        action_result = self.handle_pop_dialogs()
        verification = self.verify_order(request, action_result)
        return verification

    def cancel_order(self, entrust_no: str | None = None) -> dict[str, Any]:
        self.switch_menu(["撤单[F3]"])
        if entrust_no:
            self.select_cancel_row_by_entrust_no(entrust_no)
        result = self.click_direct_cancel_button()
        if entrust_no:
            result["entrust_no"] = entrust_no
        return result

    def switch_menu(self, path: list[str], sleep_seconds: float = 0.2) -> None:
        _, main = self.ensure_connected()
        self.close_pop_dialogs()
        tree = main.child_window(
            control_id=self.LEFT_MENU_CONTROL_ID,
            class_name="SysTreeView32",
        )
        try:
            tree.wait("ready", timeout=2)
            tree.get_item(path).select()
        except Exception as exc:
            if self._is_page_ready_for_path(path):
                time.sleep(sleep_seconds)
                return
            raise TradingClientNotReadyError(
                f"无法切换同花顺菜单 {'/'.join(path)}。交易端可能未登录或仍在启动页。"
            ) from exc
        try:
            main.type_keys("{F5}")
        except Exception:
            pass
        time.sleep(sleep_seconds)

    def _is_page_ready_for_path(self, path: list[str]) -> bool:
        target = "/".join(path)
        if "资金股票" in target:
            return self._has_balance_controls()
        if "买入" in target or "卖出" in target:
            return self._has_trade_form_controls()
        if any(name in target for name in ("当日委托", "当日成交", "历史委托", "历史成交", "撤单")):
            try:
                self._find_grid()
                return True
            except Exception:
                return False
        return False

    def _is_trade_page_ready(self) -> bool:
        try:
            _, main = self.ensure_connected()
            texts = " ".join(child.window_text() or "" for child in main.children())
            if ("登录" in texts or "资金帐户" in texts or "断开" in texts) and not self._has_balance_controls():
                return False
            if self._has_balance_controls() or self._has_trade_form_controls():
                return True
            try:
                main.child_window(
                    control_id=self.LEFT_MENU_CONTROL_ID,
                    class_name="SysTreeView32",
                ).wait("exists", timeout=1)
                return True
            except Exception:
                return False
        except Exception:
            return False

    def _has_balance_controls(self) -> bool:
        try:
            _, main = self.ensure_connected()
            found_ids = set()
            for child in main.children():
                try:
                    if child.class_name() == "Static":
                        found_ids.add(child.control_id())
                except Exception:
                    continue
            required_ids = set(self.BALANCE_CONTROL_IDS.values())
            return required_ids.issubset(found_ids)
        except Exception:
            return False

    def _has_trade_form_controls(self) -> bool:
        try:
            _, main = self.ensure_connected()
            for control_id in (
                self.TRADE_SECURITY_CONTROL_ID,
                self.TRADE_PRICE_CONTROL_ID,
                self.TRADE_AMOUNT_CONTROL_ID,
            ):
                if not main.child_window(control_id=control_id, class_name="Edit").exists(timeout=0.2):
                    return False
            return True
        except Exception:
            return False

    def _assert_trade_page_ready(self) -> None:
        if self._is_trade_page_ready():
            return
        raise TradingClientNotReadyError(
            "同花顺交易客户端已启动，但还没有进入已登录的交易界面。"
            "请先在同花顺中完成登录/连接后重试。"
        )

    def fill_trade_form(self, request: ThsOrderRequest) -> None:
        self.type_by_wm_char(self.TRADE_SECURITY_CONTROL_ID, request.symbol[-6:])
        time.sleep(0.6)
        self.type_by_wm_char(self.TRADE_PRICE_CONTROL_ID, f"{request.price:.2f}")
        self.type_by_wm_char(self.TRADE_AMOUNT_CONTROL_ID, str(int(request.quantity)))
        time.sleep(0.5)

    def type_by_wm_char(self, control_id: int, text: str, clear_first: bool = True) -> None:
        _, main = self.ensure_connected()
        wrapper = main.child_window(
            control_id=control_id,
            class_name="Edit",
        ).wrapper_object()
        hwnd = wrapper.handle
        if clear_first:
            for _ in range(24):
                win32gui.SendMessage(hwnd, win32con.WM_CHAR, 8, 0)
                time.sleep(0.01)
        for ch in text:
            win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)
            time.sleep(0.03)

    def read_grid(self) -> list[dict[str, Any]]:
        _, main = self.ensure_connected()
        grid = self._find_grid()
        self._set_foreground(grid)
        rect = grid.rectangle()
        pywinauto.mouse.click(
            button="left",
            coords=(rect.left + 20, rect.top + 20),
        )
        time.sleep(0.1)
        pywinauto.keyboard.send_keys("^a^c")
        time.sleep(0.3)
        if self._handle_captcha_dialog_if_present():
            self._set_foreground(grid)
            pywinauto.mouse.click(
                button="left",
                coords=(rect.left + 20, rect.top + 20),
            )
            time.sleep(0.1)
            pywinauto.keyboard.send_keys("^a^c")
            time.sleep(0.3)
        content = pywinauto.clipboard.GetData()
        if not content.strip():
            return []
        df = pd.read_csv(
            io.StringIO(content),
            delimiter="\t",
            dtype=self.GRID_DTYPE,
            na_filter=False,
        )
        return df.to_dict("records")

    def select_cancel_row_by_entrust_no(self, entrust_no: str) -> bool:
        # Prefer a fast, robust default: current tested cancel page auto-selects
        # the available row. If clipboard read works, click matching row.
        try:
            rows = self.read_grid()
        except Exception:
            return False
        for index, row in enumerate(rows):
            if str(row.get("合同编号", "")).strip() == entrust_no:
                self._click_grid_row(index)
                return True
        return False

    def click_direct_cancel_button(self) -> dict[str, Any]:
        _, main = self.ensure_connected()
        target = None
        for child in main.children():
            if child.class_name() != "Button":
                continue
            text = child.window_text() or ""
            rect = child.rectangle()
            if text.startswith("撤单") and rect.width() > 20 and rect.height() > 10:
                if target is None or (rect.top, rect.left) < (
                    target.rectangle().top,
                    target.rectangle().left,
                ):
                    target = child

        if target is None:
            return {
                "status": "failed",
                "method": "direct_cancel_button",
                "message": "未找到可见的撤单按钮",
            }

        target.click()
        time.sleep(1)
        dialog_result = self.handle_pop_dialogs()
        time.sleep(1)
        return {
            "status": "submitted",
            "method": "direct_cancel_button",
            "dialog_result": dialog_result,
            "balance_after": self.safe_balance(),
        }

    def handle_pop_dialogs(self) -> dict[str, Any]:
        app, main = self.ensure_connected()
        while self.is_exist_pop_dialog():
            dialog = app.top_window()
            title = self._get_dialog_title(dialog)
            content = self._extract_dialog_content(dialog)

            if self._is_captcha_dialog(dialog):
                self._handle_captcha_dialog_if_present()
                time.sleep(0.5)
                continue

            if title == "委托确认" or title == "撤单确认":
                self._submit_dialog_by_shortcut(dialog)
                time.sleep(0.5)
                continue

            if title == "提示信息":
                self._submit_dialog_by_shortcut(dialog)
                time.sleep(0.5)
                continue

            if "提示" in title:
                if "成功" in content:
                    entrust_no = self._extract_entrust_no(content)
                    self._click_confirm(dialog)
                    return {"entrust_no": entrust_no, "message": content}
                self._click_confirm(dialog)
                return {"message": content}

            try:
                dialog.close()
            except Exception:
                pass
            return {"message": f"unknown dialog: {title} {content}"}

        return {"message": "success"}

    def is_exist_pop_dialog(self) -> bool:
        app, main = self.ensure_connected()
        time.sleep(0.5)
        try:
            return main.wrapper_object() != app.top_window().wrapper_object()
        except Exception:
            return False

    def close_pop_dialogs(self) -> None:
        app, main = self.ensure_connected()
        for _ in range(3):
            if not self.is_exist_pop_dialog():
                return
            try:
                app.top_window().close()
            except Exception:
                return

    def verify_order(
        self,
        request: ThsOrderRequest,
        action_result: dict[str, Any],
    ) -> dict[str, Any]:
        errors: list[str] = []
        entrust_no = action_result.get("entrust_no")
        orders: list[dict[str, Any]] = []
        trades: list[dict[str, Any]] = []
        balance: dict[str, Any] = {}

        try:
            orders = self.get_today_orders()
        except Exception as exc:
            errors.append(f"orders: {type(exc).__name__}: {exc}")
        try:
            trades = self.get_today_trades()
        except Exception as exc:
            errors.append(f"trades: {type(exc).__name__}: {exc}")
        try:
            balance = self.get_balance()
        except Exception as exc:
            errors.append(f"balance: {type(exc).__name__}: {exc}")

        matched_orders = self._match_rows(orders, request)
        matched_trades = self._match_rows(trades, request)
        confirmed = bool(entrust_no or matched_orders or matched_trades)
        return {
            "status": "confirmed" if confirmed else "unconfirmed",
            "action_result": action_result,
            "entrust_no": entrust_no,
            "matched_orders": matched_orders,
            "matched_trades": matched_trades,
            "balance_after": balance,
            "errors": errors,
        }

    def safe_balance(self) -> dict[str, Any]:
        try:
            return self.get_balance()
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _find_grid(self):
        _, main = self.ensure_connected()
        candidates = []
        for child in main.children():
            try:
                if child.control_id() == self.COMMON_GRID_CONTROL_ID:
                    rect = child.rectangle()
                    if (
                        rect.width() > 100
                        and rect.height() > 80
                        and child.is_visible()
                    ):
                        candidates.append(child)
            except Exception:
                continue
        if not candidates:
            raise RuntimeError("未找到同花顺表格控件")
        return max(candidates, key=lambda item: item.rectangle().width() * item.rectangle().height())

    def _click_grid_row(self, index: int) -> None:
        grid = self._find_grid()
        rect = grid.rectangle()
        x = rect.left + 20
        y = rect.top + 30 + index * 18
        pywinauto.mouse.click(button="left", coords=(x, y))
        time.sleep(0.2)

    def _set_foreground(self, window: Any) -> None:
        try:
            window.set_focus()
        except Exception:
            try:
                win32gui.SetForegroundWindow(window.handle)
            except Exception:
                pass

    def _handle_captcha_dialog_if_present(self) -> bool:
        app, _ = self.ensure_connected()
        try:
            top = app.top_window()
        except Exception:
            return False

        if self._is_captcha_dialog(top):
            if self.captcha_code:
                self._submit_captcha_dialog(top, self.captcha_code)
            elif self.wait_manual_captcha:
                print(
                    f"检测到验证码弹窗，请在同花顺中手动输入验证码并点击确定，"
                    f"脚本将在最多 {self.manual_captcha_timeout} 秒内等待弹窗关闭后继续。",
                    file=sys.stderr,
                    flush=True,
                )
                self._wait_for_dialog_closed(top, self.manual_captcha_timeout)
            else:
                raise CaptchaRequiredError()
            time.sleep(0.8)
            return True
        return False

    def _is_captcha_dialog(self, dialog: Any) -> bool:
        try:
            text = " ".join(
                [dialog.window_text() or ""]
                + [child.window_text() or "" for child in dialog.children()]
            )
        except Exception:
            return False
        return "验证码" in text or "账号数据安全" in text

    def _wait_for_dialog_closed(self, dialog: Any, timeout_seconds: int) -> None:
        start = time.monotonic()
        while time.monotonic() - start <= timeout_seconds:
            try:
                if not dialog.exists(timeout=0.2) or not self._is_captcha_dialog(dialog):
                    return
            except Exception:
                return
            time.sleep(0.5)
        raise TimeoutError(f"等待人工输入验证码超时: {timeout_seconds} 秒")

    def _submit_captcha_dialog(self, dialog: Any, captcha_code: str) -> None:
        edit = None
        for child in dialog.children():
            try:
                if child.class_name() == "Edit":
                    edit = child
                    break
            except Exception:
                continue
        if edit is None:
            raise RuntimeError("检测到验证码弹窗，但未找到验证码输入框")

        hwnd = edit.handle
        for _ in range(8):
            win32gui.SendMessage(hwnd, win32con.WM_CHAR, 8, 0)
            time.sleep(0.01)
        for ch in captcha_code.strip():
            win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(ch), 0)
            time.sleep(0.03)

        for child in dialog.children():
            try:
                if child.class_name() == "Button" and "确定" in (child.window_text() or ""):
                    child.click()
                    return
            except Exception:
                continue
        raise RuntimeError("检测到验证码弹窗，但未找到确定按钮")

    def _get_dialog_title(self, dialog: Any) -> str:
        try:
            return dialog.child_window(
                control_id=self.POP_DIALOG_TITLE_CONTROL_ID
            ).window_text()
        except Exception:
            return dialog.window_text() or ""

    def _extract_dialog_content(self, dialog: Any) -> str:
        texts: list[str] = []
        for child in dialog.children():
            try:
                if child.class_name() == "Static":
                    text = child.window_text()
                    if text:
                        texts.append(text)
            except Exception:
                continue
        return " ".join(texts)

    def _submit_dialog_by_shortcut(self, dialog: Any) -> None:
        self._set_foreground(dialog)
        try:
            dialog.type_keys("%Y", set_foreground=False)
        except Exception:
            self._click_confirm(dialog)

    def _click_confirm(self, dialog: Any) -> None:
        for child in dialog.children():
            try:
                if child.class_name() == "Button" and "确定" in (child.window_text() or ""):
                    child.click()
                    return
            except Exception:
                continue
        try:
            dialog["确定"].click()
        except Exception:
            pass

    def _extract_entrust_no(self, content: str) -> str | None:
        match = re.search(r"[\da-zA-Z]+", content)
        return match.group() if match else None

    def _match_rows(self, rows: Any, request: ThsOrderRequest) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        symbol = request.symbol[-6:]
        matched: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_symbol = str(row.get("证券代码", "")).strip()
            row_quantity = int(float(row.get("委托数量", 0) or 0))
            row_price = Decimal(str(row.get("委托价格", 0) or 0))
            if row_symbol and row_symbol != symbol:
                continue
            if row_quantity and row_quantity != request.quantity:
                continue
            if row_price and abs(row_price - request.price) > Decimal("0.001"):
                continue
            if row_symbol or row_quantity or row_price:
                matched.append(row)
        return matched


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="THS desktop adapter CLI")
    parser.add_argument("--client-path", required=True)
    parser.add_argument(
        "--operation",
        required=True,
        choices=[
            "status",
            "balance",
            "positions",
            "orders",
            "trades",
            "history-orders",
            "history-trades",
            "buy",
            "sell",
            "cancel",
        ],
    )
    parser.add_argument("--symbol")
    parser.add_argument("--price")
    parser.add_argument("--quantity", type=int)
    parser.add_argument("--entrust-no")
    parser.add_argument("--captcha-code", help="人工识别后的验证码")
    parser.add_argument(
        "--wait-manual-captcha",
        action="store_true",
        help="检测到验证码弹窗时等待人工在同花顺中输入并确认，然后继续流程",
    )
    parser.add_argument(
        "--manual-captcha-timeout",
        type=int,
        default=120,
        help="等待人工处理验证码弹窗的最长秒数，默认 120",
    )
    args = parser.parse_args()

    adapter = ThsDesktopAdapter(
        args.client_path,
        captcha_code=args.captcha_code,
        wait_manual_captcha=args.wait_manual_captcha,
        manual_captcha_timeout=args.manual_captcha_timeout,
    )
    adapter.connect()

    if args.operation == "status":
        result = adapter.status()
    elif args.operation == "balance":
        result = adapter.get_balance()
    elif args.operation == "positions":
        result = adapter.get_positions()
    elif args.operation == "orders":
        result = adapter.get_today_orders()
    elif args.operation == "trades":
        result = adapter.get_today_trades()
    elif args.operation == "history-orders":
        result = adapter.get_history_orders()
    elif args.operation == "history-trades":
        result = adapter.get_history_trades()
    elif args.operation in {"buy", "sell"}:
        if not args.symbol or not args.price or args.quantity is None:
            raise SystemExit("buy/sell requires --symbol --price --quantity")
        if args.operation == "buy":
            result = adapter.buy(args.symbol, args.price, args.quantity)
        else:
            result = adapter.sell(args.symbol, args.price, args.quantity)
    elif args.operation == "cancel":
        result = adapter.cancel_order(args.entrust_no)
    else:
        raise SystemExit(f"unsupported operation: {args.operation}")

    print(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
