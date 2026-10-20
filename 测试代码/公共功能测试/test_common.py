from contextlib import closing
"""公共基础模块单元/集成测试：接口、数据库、数据完整性与可复用性。"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import create_app
from 功能代码及实际项目文件.公共基础模块.db import connect, initialize_database
from 功能代码及实际项目文件.公共基础模块.errors import BusinessError, envelope


def test_envelope_has_stable_shape():
    assert envelope("OK", "success", {"a": 1}) == {
        "code": "OK", "message": "success", "data": {"a": 1}}
    assert envelope("ERROR", "failed")["data"] is None


def test_business_error_fields():
    error = BusinessError(404, "MISSING", "not found")
    assert (error.status, error.code, error.message) == (404, "MISSING", "not found")


def test_health_reaches_database(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "ok"


def test_home_redirects_to_student_page(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/student"


def test_student_web_page_is_served(client):
    response = client.get("/student")
    assert response.status_code == 200
    assert 'id="timetable"' in response.text
    assert 'id="courses"' in response.text
    assert "X-Demo-User" in response.text


def test_openapi_exposes_student_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/students/me/timetable" in paths
    assert "/api/v1/students/me/courses/{course_id}/outline" in paths


def test_initialization_is_idempotent(tmp_path: Path):
    db_path = tmp_path / "idempotent.sqlite3"
    initialize_database(db_path)
    initialize_database(db_path)
    with closing(connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 6
        assert conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0] == 5
        assert conn.execute("SELECT COUNT(*) FROM schedules").fetchone()[0] == 4


def test_foreign_key_checks_enabled(tmp_path: Path):
    db_path = tmp_path / "integrity.sqlite3"
    initialize_database(db_path)
    with closing(connect(db_path)) as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(__import__("sqlite3").IntegrityError):
            conn.execute("INSERT INTO enrollments VALUES (?,?)", ("missing", "CS101"))


def test_database_path_can_be_injected_without_seed(tmp_path: Path):
    db_path = tmp_path / "isolation" / "empty.sqlite3"
    with TestClient(create_app(db_path, seed=False)) as client:
        assert client.get("/api/v1/health").status_code == 200
    with closing(connect(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0] == 0
