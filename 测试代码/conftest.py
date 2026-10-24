"""使用临时数据库运行测试：不修改真实演示数据库。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 无需安装成 wheel，直接从项目根目录运行 pytest 即可。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import create_app  # noqa: E402


@pytest.fixture
def client(tmp_path: Path):
    """每个用例使用新建 SQLite 文件，杜绝用例之间的数据串扰。"""
    app = create_app(tmp_path / "sprint_test.sqlite3")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def student_headers() -> dict[str, str]:
    return {"X-Demo-User": "S2024001"}


@pytest.fixture
def teacher_headers() -> dict[str, str]:
    """张老师：主讲 SE201、协讲 MA101，覆盖"一位教师多门课"的场景。"""
    return {"X-Demo-User": "T003"}
