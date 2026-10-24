"""项目配置：统一管理本地 SQLite 数据库位置。"""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def database_path() -> Path:
    """支持环境变量覆盖数据库路径，方便开发、测试使用隔离的数据文件。"""
    value = os.environ.get("DATABASE_PATH")
    return Path(value).expanduser().resolve() if value else PROJECT_ROOT / "data" / "sprint1_backup.sqlite3"
