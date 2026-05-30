"""
API Data 模块数据库初始化脚本
用于创建 stock_base_info, kline_data, realtime_quote, sector_info 表
"""

import asyncio
from sqlalchemy import text

from common.database import engine, Base
from api_data.models import (
    StockBaseInfoModel,
    KLineDataModel,
    RealtimeQuoteModel,
    SectorInfoModel,
)


async def create_tables():
    """创建所有 api_data 模块的表"""
    async with engine.begin() as conn:
        print("创建 stock_base_info 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_base_info (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL UNIQUE COMMENT '股票代码',
                name VARCHAR(100) COMMENT '股票名称',
                market VARCHAR(10) COMMENT '市场类型 A/HK/US',
                sector VARCHAR(100) COMMENT '所属行业板块',
                IPO_date VARCHAR(20) COMMENT '上市日期',
                total_shares FLOAT COMMENT '总股本(万股)',
                float_shares FLOAT COMMENT '流通股本(万股)',
                status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/suspended/delisted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        print("  ✓ stock_base_info 表创建完成")

        print("创建 kline_data 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kline_data (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL COMMENT '股票代码',
                timeframe VARCHAR(10) NOT NULL COMMENT '时间周期 1m/5m/15m/30m/1h/1d/1w',
                timestamp TIMESTAMP NOT NULL COMMENT 'K线时间戳',
                open FLOAT NOT NULL COMMENT '开盘价',
                high FLOAT NOT NULL COMMENT '最高价',
                low FLOAT NOT NULL COMMENT '最低价',
                close FLOAT NOT NULL COMMENT '收盘价',
                volume FLOAT NOT NULL COMMENT '成交量',
                turnover FLOAT COMMENT '成交额',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_symbol_timeframe_timestamp (symbol, timeframe, timestamp),
                INDEX idx_symbol_timeframe (symbol, timeframe),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        print("  ✓ kline_data 表创建完成")

        print("创建 realtime_quote 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS realtime_quote (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                symbol VARCHAR(20) NOT NULL UNIQUE COMMENT '股票代码',
                name VARCHAR(100) COMMENT '股票名称',
                last_price FLOAT NOT NULL COMMENT '最新价',
                `change` FLOAT COMMENT '涨跌额',
                change_pct FLOAT COMMENT '涨跌幅(%)',
                `open` FLOAT COMMENT '开盘价',
                high_price FLOAT COMMENT '最高价',
                low_price FLOAT COMMENT '最低价',
                volume FLOAT COMMENT '成交量',
                turnover FLOAT COMMENT '成交额',
                amplitude FLOAT COMMENT '振幅(%)',
                market_cap FLOAT COMMENT '总市值',
                float_market_cap FLOAT COMMENT '流通市值',
                pe_ratio FLOAT COMMENT '市盈率',
                pb_ratio FLOAT COMMENT '市净率',
                quote_timestamp TIMESTAMP COMMENT '数据时间戳',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        print("  ✓ realtime_quote 表创建完成")

        print("创建 sector_info 表...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sector_info (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                sector_code VARCHAR(50) NOT NULL UNIQUE COMMENT '板块代码',
                sector_name VARCHAR(100) COMMENT '板块名称',
                market VARCHAR(10) COMMENT '市场类型',
                stock_count INT DEFAULT 0 COMMENT '成分股数量',
                description TEXT COMMENT '板块描述',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_sector_code (sector_code)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))
        print("  ✓ sector_info 表创建完成")

    print("\n所有表创建完成！")


async def drop_tables():
    """删除所有 api_data 模块的表（谨慎使用）"""
    async with engine.begin() as conn:
        print("删除 sector_info 表...")
        await conn.execute(text("DROP TABLE IF EXISTS sector_info"))
        print("删除 realtime_quote 表...")
        await conn.execute(text("DROP TABLE IF EXISTS realtime_quote"))
        print("删除 kline_data 表...")
        await conn.execute(text("DROP TABLE IF EXISTS kline_data"))
        print("删除 stock_base_info 表...")
        await conn.execute(text("DROP TABLE IF EXISTS stock_base_info"))

    print("\n所有表已删除")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        print("警告: 将删除所有 api_data 模块的表！")
        confirm = input("确认删除? (yes/no): ")
        if confirm.lower() == "yes":
            asyncio.run(drop_tables())
        else:
            print("取消删除")
    else:
        asyncio.run(create_tables())
