"""异常与权限边界测试：越权、未登录、参数错误、未发布及数据库故障。"""
import pytest


@pytest.mark.parametrize("path", [
    "/api/v1/students/me/courses",
    "/api/v1/students/me/timetable",
    "/api/v1/students/me/courses/CS101/outline",
])
def test_missing_identity_returns_401(client, path):
    res = client.get(path)
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"
    assert res.json()["data"] is None


def test_blank_identity_returns_401(client):
    res = client.get("/api/v1/students/me/courses", headers={"X-Demo-User": ""})
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"


def test_unknown_student_identity_returns_401(client):
    res = client.get("/api/v1/students/me/courses", headers={"X-Demo-User": "S0000000"})
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


@pytest.mark.parametrize("user", ["T001", "D001", "V001"])
def test_non_student_roles_forbidden(client, user):
    res = client.get("/api/v1/students/me/timetable?week=1", headers={"X-Demo-User": user})
    assert res.status_code == 403
    assert res.json()["code"] == "ROLE_FORBIDDEN"


@pytest.mark.parametrize("week", ["0", "21", "-1", "abc", "1.2", "999999999999999999999999999"])
def test_invalid_week_returns_standard_422(client, student_headers, week):
    res = client.get(f"/api/v1/students/me/timetable?week={week}", headers=student_headers)
    assert res.status_code == 422
    assert res.json() == {"code": "PARAM_INVALID", "message": "请求参数格式或范围不正确", "data": None}


def test_course_from_another_student_is_not_visible(client):
    res = client.get("/api/v1/students/me/courses/CS101/outline", headers={"X-Demo-User": "S2024002"})
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


def test_nonexistent_course_returns_404(client, student_headers):
    res = client.get("/api/v1/students/me/courses/NOT_FOUND/outline", headers=student_headers)
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


def test_unpublished_outline_not_disclosed(client, student_headers):
    res = client.get("/api/v1/students/me/courses/AI999/outline", headers=student_headers)
    assert res.status_code == 404
    assert res.json()["code"] == "OUTLINE_UNAVAILABLE"
    assert res.json()["data"] is None


def test_sql_injection_like_identity_does_not_bypass_role(client):
    res = client.get("/api/v1/students/me/courses", headers={"X-Demo-User": "' OR 1=1 --"})
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


def test_sql_injection_like_course_id_does_not_bypass_enrollment(client, student_headers):
    res = client.get("/api/v1/students/me/courses/CS101%27%20OR%201%3D1--/outline", headers=student_headers)
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


def test_database_failure_returns_sanitized_503(client, tmp_path):
    client.app.state.db_path = tmp_path / "missing_directory" / "broken.sqlite3"
    res = client.get("/api/v1/health")
    assert res.status_code == 503
    assert res.json()["code"] == "DB_UNAVAILABLE"
    assert "sqlite" not in res.text.lower()
