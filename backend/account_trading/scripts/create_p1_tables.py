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
import review_analysis.models  # noqa: E402,F401
from account_trading.scripts.create_p0_tables import P0_TABLE_NAMES  # noqa: E402


P1_TABLE_NAMES = (
    "live_cash_flow",
    "paper_cash_flow",
    "backtest_cash_flow",
    "paper_simulation_run",
    "review_session",
    "review_metric_snapshot",
    "review_trade_item",
    "review_equity_curve",
    "review_drawdown_curve",
    "review_suggestion",
)


async def create_p1_tables(include_p0: bool = True) -> None:
    table_names = (*P0_TABLE_NAMES, *P1_TABLE_NAMES) if include_p0 else P1_TABLE_NAMES
    tables = [Base.metadata.tables[name] for name in table_names]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables, checkfirst=True))
    await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create P1 account trading and review analysis tables.")
    parser.add_argument("--dry-run", action="store_true", help="Only print table names, do not connect to database.")
    parser.add_argument("--p1-only", action="store_true", help="Create only P1 tables. Use only when P0 tables already exist.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.p1_only:
        print("P0 dependency tables:")
        for table_name in P0_TABLE_NAMES:
            print(f"- {table_name}")

    print("P1 tables:")
    for table_name in P1_TABLE_NAMES:
        print(f"- {table_name}")

    if args.dry_run:
        return

    asyncio.run(create_p1_tables(include_p0=not args.p1_only))
    print("P1 tables are ready.")


if __name__ == "__main__":
    main()
