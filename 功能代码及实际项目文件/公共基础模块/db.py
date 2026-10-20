"""数据库连接与初始化：所有端共享 SQLite 表结构、参数化查询规范。"""
from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterator

from fastapi import Request

from .seed import seed_demo


def connect(db_path: Path) -> sqlite3.Connection:
    """使用 Row 返回字典式字段；每次连接开启外键完整性校验。"""
    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(db_path: Path, *, seed: bool = True) -> None:
    """建表和数据初始化支持重复调用，不清空已有数据库。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")
    with closing(connect(db_path)) as conn:
        with conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            if seed:
                seed_demo(conn)


def get_db(request: Request) -> Iterator[sqlite3.Connection]:
    """FastAPI 依赖：每个请求独立连接，请求结束后自动释放。"""
    conn = connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()
