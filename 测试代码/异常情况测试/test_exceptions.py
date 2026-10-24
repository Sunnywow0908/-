"""异常与权限边界测试：越权、未登录、参数错误、未发布及数据库故障。

覆盖学生端与教师端两条链路，重点验证"教师只能看到自己教的课"这条权限边界。
"""
from contextlib import closing

import pytest

from 功能代码及实际项目文件.公共基础模块.db import connect


TEACHER_ENDPOINTS = [
    "/api/v1/teachers/me/courses",
    "/api/v1/teachers/me/timetable?week=1",
    "/api/v1/teachers/me/courses/SE201/students",
    "/api/v1/teachers/me/courses/SE201/outline",
]


def teacher_headers(teacher_id: str) -> dict[str, str]:
    return {"X-Demo-User": teacher_id}


def make_course_without_outline(client, course_id: str, teacher_id: str) -> None:
    """构造一门没有大纲记录的课程，用于"草稿缺失"分支。"""
    with closing(connect(client.app.state.db_path)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO courses(id, name, teacher_name, credits, outline_published)"
                " VALUES (?, ?, ?, 1.0, 0)",
                (course_id, "待发布课程", "测试教师"),
            )
            conn.execute(
                "INSERT INTO course_teachers(course_id, teacher_id, duty) VALUES (?, ?, '主讲')",
                (course_id, teacher_id),
            )


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


# =============================== 教师端：身份与角色 ===============================


@pytest.mark.parametrize("path", TEACHER_ENDPOINTS)
def test_teacher_missing_identity_returns_401(client, path):
    res = client.get(path)
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"
    assert res.json()["data"] is None


@pytest.mark.parametrize("path", TEACHER_ENDPOINTS)
def test_teacher_empty_identity_returns_401(client, path):
    res = client.get(path, headers={"X-Demo-User": ""})
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("path", TEACHER_ENDPOINTS)
@pytest.mark.parametrize("blank", ["  ", "\t", "   "])
def test_teacher_whitespace_identity_returns_401(client, path, blank):
    """纯空白标识不会被当作合法学号，按未知身份处理，避免绕过角色校验。"""
    res = client.get(path, headers={"X-Demo-User": blank})
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


def test_teacher_unknown_identity_returns_401(client):
    res = client.get("/api/v1/teachers/me/courses", headers={"X-Demo-User": "T999"})
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


@pytest.mark.parametrize("user", ["S2024001", "S2024003", "D001", "V001"])
def test_teacher_end_forbidden_for_non_teacher_roles(client, user):
    res = client.get("/api/v1/teachers/me/courses", headers={"X-Demo-User": user})
    assert res.status_code == 403
    assert res.json()["code"] == "ROLE_FORBIDDEN"


@pytest.mark.parametrize("path", ["/api/v1/students/me/courses", "/api/v1/students/me/timetable?week=1"])
def test_student_end_forbidden_for_teacher_roles(client, path):
    """角色隔离是双向的：教师不能借学生端接口读取数据。"""
    res = client.get(path, headers=teacher_headers("T003"))
    assert res.status_code == 403
    assert res.json()["code"] == "ROLE_FORBIDDEN"


# =============================== 教师端：参数与越权 ===============================


@pytest.mark.parametrize("week", ["0", "21", "-1", "abc", "1.5", "999999999999999999999"])
def test_teacher_invalid_week_returns_standard_422(client, week):
    res = client.get(f"/api/v1/teachers/me/timetable?week={week}", headers=teacher_headers("T003"))
    assert res.status_code == 422
    assert res.json() == {"code": "PARAM_INVALID", "message": "请求参数格式或范围不正确", "data": None}


@pytest.mark.parametrize("path", [
    "/api/v1/teachers/me/courses/CS101/students",
    "/api/v1/teachers/me/courses/CS101/outline",
])
def test_course_taught_by_another_teacher_is_not_visible(client, path):
    """张老师（T003）不得查看李老师（T002）的 CS101。"""
    res = client.get(path, headers=teacher_headers("T003"))
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"
    assert res.json()["data"] is None


def test_teacher_without_assignment_cannot_read_any_course(client):
    """教师甲（T001）没有授课关系，任何按课程 id 的访问都应被拒绝。"""
    res = client.get("/api/v1/teachers/me/courses/SE201/students", headers=teacher_headers("T001"))
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


@pytest.mark.parametrize("path", [
    "/api/v1/teachers/me/courses/NOT_FOUND/students",
    "/api/v1/teachers/me/courses/NOT_FOUND/outline",
])
def test_nonexistent_course_returns_404(client, path):
    res = client.get(path, headers=teacher_headers("T003"))
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


def test_sql_injection_like_teacher_identity_does_not_bypass_role(client):
    res = client.get("/api/v1/teachers/me/courses", headers={"X-Demo-User": "' OR 1=1 --"})
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


@pytest.mark.parametrize("suffix", ["students", "outline"])
def test_sql_injection_like_course_id_does_not_bypass_teaching_check(client, suffix):
    res = client.get(
        f"/api/v1/teachers/me/courses/SE201%27%20OR%201%3D1--/{suffix}",
        headers=teacher_headers("T003"),
    )
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


def test_sql_injection_like_course_id_cannot_write_outline(client):
    res = client.put(
        "/api/v1/teachers/me/courses/SE201%27%3B--/outline",
        headers=teacher_headers("T003"),
        json={"summary": "a", "objectives": "b", "chapters": "c", "assessment": "d"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"


def test_writing_another_teachers_course_leaves_data_untouched(client):
    """越权写入必须既报错又不产生任何副作用。"""
    with closing(connect(client.app.state.db_path)) as conn:
        before = conn.execute(
            "SELECT summary FROM course_outlines WHERE course_id = 'CS101'"
        ).fetchone()[0]
    res = client.put(
        "/api/v1/teachers/me/courses/CS101/outline",
        headers=teacher_headers("T003"),
        json={"summary": "越权内容", "objectives": "越权目标", "chapters": "越权章节", "assessment": "越权考核"},
    )
    assert res.status_code == 404
    with closing(connect(client.app.state.db_path)) as conn:
        after = conn.execute(
            "SELECT summary FROM course_outlines WHERE course_id = 'CS101'"
        ).fetchone()[0]
    assert before == after


# =============================== 教师端：大纲状态机 ===============================


def test_published_outline_cannot_be_edited(client):
    res = client.put(
        "/api/v1/teachers/me/courses/SE201/outline",
        headers=teacher_headers("T003"),
        json={"summary": "a", "objectives": "b", "chapters": "c", "assessment": "d"},
    )
    assert res.status_code == 409
    assert res.json()["code"] == "OUTLINE_LOCKED"
    assert res.json()["data"] is None


def test_publishing_outline_twice_returns_409(client):
    res = client.post("/api/v1/teachers/me/courses/SE201/outline/publish", headers=teacher_headers("T003"))
    assert res.status_code == 409
    assert res.json()["code"] == "OUTLINE_ALREADY_PUBLISHED"


def test_unpublishing_draft_outline_returns_409(client):
    """AI999 初始为未发布状态，撤回操作应被拒绝而不是静默成功。"""
    res = client.post("/api/v1/teachers/me/courses/AI999/outline/unpublish", headers=teacher_headers("T005"))
    assert res.status_code == 409
    assert res.json()["code"] == "OUTLINE_NOT_PUBLISHED"


def test_publishing_without_draft_returns_409(client):
    make_course_without_outline(client, "NODRAFT1", "T003")
    res = client.post("/api/v1/teachers/me/courses/NODRAFT1/outline/publish", headers=teacher_headers("T003"))
    assert res.status_code == 409
    assert res.json()["code"] == "OUTLINE_INCOMPLETE"


def test_outline_state_machine_rejects_writes_on_foreign_course(client):
    """状态机校验必须发生在授课权限校验之后，且不泄露他人课程是否已发布。"""
    for path, method in [
        ("/api/v1/teachers/me/courses/CS101/outline/publish", "post"),
        ("/api/v1/teachers/me/courses/CS101/outline/unpublish", "post"),
    ]:
        res = getattr(client, method)(path, headers=teacher_headers("T003"))
        assert res.status_code == 404
        assert res.json()["code"] == "COURSE_NOT_FOUND"


# =============================== 教师端：请求体校验 ===============================


@pytest.mark.parametrize("payload", [
    {},
    {"summary": "a", "objectives": "b", "chapters": "c"},
    {"summary": "a", "objectives": "b", "assessment": "d"},
])
def test_outline_draft_missing_fields_returns_422(client, payload):
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline", headers=teacher_headers("T005"), json=payload
    )
    assert res.status_code == 422
    assert res.json() == {"code": "PARAM_INVALID", "message": "请求参数格式或范围不正确", "data": None}


@pytest.mark.parametrize("blank", ["", "   ", "\n\t "])
def test_outline_draft_blank_field_returns_422(client, blank):
    payload = {"summary": "a", "objectives": "b", "chapters": "c", "assessment": "d"}
    payload["summary"] = blank
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline", headers=teacher_headers("T005"), json=payload
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PARAM_INVALID"


@pytest.mark.parametrize("field", ["summary", "objectives", "chapters", "assessment"])
def test_outline_draft_overlong_field_returns_422(client, field):
    payload = {"summary": "a", "objectives": "b", "chapters": "c", "assessment": "d"}
    payload[field] = "长" * 1200
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline", headers=teacher_headers("T005"), json=payload
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PARAM_INVALID"


@pytest.mark.parametrize("payload", [
    {"summary": 1, "objectives": "b", "chapters": "c", "assessment": "d"},
    {"summary": ["a"], "objectives": "b", "chapters": "c", "assessment": "d"},
    {"summary": None, "objectives": "b", "chapters": "c", "assessment": "d"},
    {"summary": {"text": "a"}, "objectives": "b", "chapters": "c", "assessment": "d"},
])
def test_outline_draft_wrong_type_returns_422(client, payload):
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline", headers=teacher_headers("T005"), json=payload
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PARAM_INVALID"


def test_invalid_outline_body_does_not_create_a_draft(client):
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline",
        headers=teacher_headers("T005"),
        json={"summary": "   ", "objectives": "", "chapters": "", "assessment": ""},
    )
    assert res.status_code == 422
    with closing(connect(client.app.state.db_path)) as conn:
        stored = conn.execute(
            "SELECT summary FROM course_outlines WHERE course_id = 'AI999'"
        ).fetchone()[0]
    assert stored == "暂未对学生开放的课程大纲。"


def test_teacher_end_database_failure_returns_sanitized_503(client, tmp_path):
    client.app.state.db_path = tmp_path / "missing_directory" / "broken.sqlite3"
    res = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T003"))
    assert res.status_code == 503
    assert res.json()["code"] == "DB_UNAVAILABLE"
    assert "sqlite" not in res.text.lower()


# =============================== 教研室主任端：身份与角色 ===============================


DIRECTOR_ENDPOINTS = [
    "/api/v1/directors/me/teachers",
    "/api/v1/directors/me/courses",
    "/api/v1/directors/me/courses/CS101/summary",
    "/api/v1/directors/me/offerings",
]


def director_headers(director_id: str = "D001") -> dict[str, str]:
    return {"X-Demo-User": director_id}


@pytest.mark.parametrize("path", DIRECTOR_ENDPOINTS)
def test_director_missing_identity_returns_401(client, path):
    res = client.get(path)
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"
    assert res.json()["data"] is None


@pytest.mark.parametrize("path", DIRECTOR_ENDPOINTS)
def test_director_empty_identity_returns_401(client, path):
    res = client.get(path, headers={"X-Demo-User": ""})
    assert res.status_code == 401
    assert res.json()["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("path", DIRECTOR_ENDPOINTS)
@pytest.mark.parametrize("blank", ["  ", "\t", "   "])
def test_director_whitespace_identity_returns_401(client, path, blank):
    """纯空白标识按未知身份处理，与公共身份解析规则一致。"""
    res = client.get(path, headers={"X-Demo-User": blank})
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


@pytest.mark.parametrize("path", DIRECTOR_ENDPOINTS)
def test_director_unknown_identity_returns_401(client, path):
    res = client.get(path, headers=director_headers("D999"))
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


@pytest.mark.parametrize("path", DIRECTOR_ENDPOINTS)
@pytest.mark.parametrize("user", ["S2024001", "T003", "V001"])
def test_director_end_forbidden_for_non_director_roles(client, path, user):
    res = client.get(path, headers={"X-Demo-User": user})
    assert res.status_code == 403
    assert res.json()["code"] == "ROLE_FORBIDDEN"


def test_director_without_scope_returns_403(client):
    """用户角色是主任，但未分配管理范围时仍不能查询。"""
    with closing(connect(client.app.state.db_path)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO users(id, name, role) VALUES (?, ?, ?)",
                ("D999", "未分配范围的主任", "director"),
            )

    res = client.get(
        "/api/v1/directors/me/courses",
        headers=director_headers("D999"),
    )
    assert res.status_code == 403
    assert res.json()["code"] == "SCOPE_UNASSIGNED"


# =============================== 教研室主任端：参数与越权 ===============================


@pytest.mark.parametrize("endpoint", ["courses", "offerings"])
@pytest.mark.parametrize("teacher_id", ["T004", "NOT_FOUND"])
def test_director_foreign_or_unknown_teacher_returns_404(
    client, endpoint, teacher_id
):
    """D001不能查询其他教研室的T004，未知教师使用相同错误码。"""
    res = client.get(
        f"/api/v1/directors/me/{endpoint}",
        params={"teacher_id": teacher_id},
        headers=director_headers(),
    )
    assert res.status_code == 404
    assert res.json()["code"] == "TEACHER_NOT_FOUND"
    assert res.json()["data"] is None


@pytest.mark.parametrize("course_id", ["CS101", "NOT_FOUND"])
def test_director_foreign_or_unknown_course_returns_404(client, course_id):
    """数学教研室主任D002不能查看软件工程教师的CS101。"""
    res = client.get(
        f"/api/v1/directors/me/courses/{course_id}/summary",
        headers=director_headers("D002"),
    )
    assert res.status_code == 404
    assert res.json()["code"] == "COURSE_NOT_FOUND"
    assert res.json()["data"] is None


@pytest.mark.parametrize(
    "teacher_id",
    ["", "a" * 33, "' OR 1=1 --", "<script>"],
)
def test_director_invalid_teacher_id_returns_422(client, teacher_id):
    res = client.get(
        "/api/v1/directors/me/courses",
        params={"teacher_id": teacher_id},
        headers=director_headers(),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PARAM_INVALID"


@pytest.mark.parametrize("semester", [
    "2026",
    "2026-2027-3",
    "2026-2028-1",
    "' OR 1=1 --",
])
def test_director_invalid_semester_returns_422(client, semester):
    res = client.get(
        "/api/v1/directors/me/offerings",
        params={"semester": semester},
        headers=director_headers(),
    )
    assert res.status_code == 422
    assert res.json()["code"] == "PARAM_INVALID"


def test_director_sql_injection_identity_does_not_bypass_role(client):
    res = client.get(
        "/api/v1/directors/me/courses",
        headers={"X-Demo-User": "' OR 1=1 --"},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "USER_UNKNOWN"


def test_director_department_parameter_cannot_override_scope(client):
    """客户端传入其他教研室编号，不能扩大服务端管理范围。"""
    res = client.get(
        "/api/v1/directors/me/courses",
        params={"department_id": "MA"},
        headers=director_headers(),
    )
    assert res.status_code == 200

    items = res.json()["data"]["items"]
    assert "T004" not in {item["teacher_id"] for item in items}


# =============================== 教研室主任端：简介缺失与发布状态 ===============================


@pytest.mark.parametrize("mode", ["missing", "blank"])
def test_director_missing_or_blank_summary_has_explicit_message(client, mode):
    with closing(connect(client.app.state.db_path)) as conn:
        with conn:
            if mode == "missing":
                conn.execute(
                    "DELETE FROM course_outlines WHERE course_id = ?",
                    ("CS101",),
                )
            else:
                conn.execute(
                    "UPDATE course_outlines SET summary = ? WHERE course_id = ?",
                    ("   ", "CS101"),
                )

    res = client.get(
        "/api/v1/directors/me/courses/CS101/summary",
        headers=director_headers(),
    )
    assert res.status_code == 200
    assert res.json()["data"]["summary"] == "暂无课程简介"
    assert res.json()["data"]["summary_available"] is False


def test_director_unpublished_summary_not_disclosed(client):
    res = client.get(
        "/api/v1/directors/me/courses/AI999/summary",
        headers=director_headers(),
    )
    assert res.status_code == 200
    assert res.json()["data"]["summary"] == "课程简介尚未发布"
    assert res.json()["data"]["summary_available"] is False
    assert "暂未对学生开放的课程大纲" not in res.text


# =============================== 教研室主任端：数据库故障 ===============================


@pytest.mark.parametrize("path", DIRECTOR_ENDPOINTS)
def test_director_database_failure_returns_sanitized_503(client, tmp_path, path):
    client.app.state.db_path = tmp_path / "missing_directory" / "broken.sqlite3"

    res = client.get(path, headers=director_headers())

    assert res.status_code == 503
    assert res.json() == {
        "code": "DB_UNAVAILABLE",
        "message": "数据服务暂不可用",
        "data": None,
    }
    assert "sqlite" not in res.text.lower()