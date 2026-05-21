from typing import Annotated
from fastapi import Depends
from .database import get_db
from .config import get_settings, Settings

# Lazy import to avoid circular dependency
_data_source = None


def get_data_source():
    """获取数据源适配器（全局单例，延迟加载）"""
    global _data_source
    if _data_source is None:
        from api_data.adapters.mock import MockAdapter
        _data_source = MockAdapter()
    return _data_source


__all__ = ["get_db", "get_settings", "Settings", "get_data_source"]