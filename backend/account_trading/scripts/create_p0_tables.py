from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent

os.chdir(PROJECT_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from common.database import Base, engine  # noqa: E402
import account_trading.models  # noqa: E402,F401


P0_TABLE_NAMES = (
    "trading_account",
    "account_binding",
    "account_runtime_status",
    "account_operation_task",
    "account_operation_step",
    "live_balance_snapshot",
    "live_position_snapshot",
    "live_order",
    "live_trade",
    "live_order_status_log",
    "paper_balance_snapshot",
    "paper_position_snapshot",
    "paper_order",
    "paper_trade",
    "paper_order_status_log",
    "backtest_run",
    "backtest_balance_snapshot",
    "backtest_position_snapshot",
    "backtest_order",
    "backtest_trade",
    "backtest_order_status_log",
)


async def create_p0_tables() -> None:
    tables = [Base.metadata.tables[name] for name in P0_TABLE_NAMES]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables, checkfirst=True))
    await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create P0 account trading tables.")
    parser.add_argument("--dry-run", action="store_true", help="Only print table names, do not connect to database.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print("P0 tables:")
    for table_name in P0_TABLE_NAMES:
        print(f"- {table_name}")

    if args.dry_run:
        return

    asyncio.run(create_p0_tables())
    print("P0 tables are ready.")


if __name__ == "__main__":
    main()
