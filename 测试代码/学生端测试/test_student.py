"""学生端功能与单元测试：用户故事 US-S01 / US-S02 / US-S03。"""
import sqlite3

from 功能代码及实际项目文件.学生端.service import (
    WEEKDAY_NAMES,
    get_course_outline,
    get_timetable,
    list_my_courses,
)
from 功能代码及实际项目文件.公共基础模块.db import connect


def test_student_courses_list(client, student_headers):
    res = client.get("/api/v1/students/me/courses", headers=student_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 4
    assert {course["course_id"] for course in data["items"]} == {
        "CS101", "SE201", "MA101", "AI999"
    }


def test_student_courses_include_outline_status(client, student_headers):
    data = client.get("/api/v1/students/me/courses", headers=student_headers).json()["data"]
    rows = {course["course_id"]: course for course in data["items"]}
    assert rows["CS101"]["outline_published"] is True
    assert rows["AI999"]["outline_published"] is False
    assert rows["CS101"]["credits"] == 3.0


def test_student_two_sees_only_own_course(client):
    data = client.get("/api/v1/students/me/courses", headers={"X-Demo-User":"S2024002"}).json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["course_id"] == "SE201"


def test_unenrolled_student_has_empty_course_list(client):
    data = client.get("/api/v1/students/me/courses", headers={"X-Demo-User":"S2024003"}).json()["data"]
    assert data == {"total": 0, "items": []}


def test_default_week_is_first_week(client, student_headers):
    data = client.get("/api/v1/students/me/timetable", headers=student_headers).json()["data"]
    assert data["week"] == 1
    assert data["total"] == 3


def test_week_one_timetable_sorted_and_fields_correct(client, student_headers):
    data = client.get("/api/v1/students/me/timetable?week=1", headers=student_headers).json()["data"]
    assert [r["course_id"] for r in data["items"]] == ["CS101", "SE201", "MA101"]
    assert [r["weekday"] for r in data["items"]] == [1, 2, 4]
    assert data["items"][0]["weekday_name"] == "周一"
    assert data["items"][0]["start_section"] == 1
    assert data["items"][0]["classroom"] == "教学楼 A101"


def test_week_ten_adds_course_that_starts_later(client, student_headers):
    data = client.get("/api/v1/students/me/timetable?week=10", headers=student_headers).json()["data"]
    assert data["total"] == 4
    assert data["items"][-1]["course_id"] == "AI999"


def test_week_seventeen_excludes_ended_courses(client, student_headers):
    data = client.get("/api/v1/students/me/timetable?week=17", headers=student_headers).json()["data"]
    assert {r["course_id"] for r in data["items"]} == {"SE201", "MA101"}


def test_week_twenty_includes_last_week_boundary(client, student_headers):
    data = client.get("/api/v1/students/me/timetable?week=20", headers=student_headers).json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["course_id"] == "MA101"


def test_student_two_has_only_own_timetable(client):
    data = client.get("/api/v1/students/me/timetable?week=1", headers={"X-Demo-User":"S2024002"}).json()["data"]
    assert data["student_id"] == "S2024002"
    assert [r["course_id"] for r in data["items"]] == ["SE201"]


def test_unenrolled_student_has_empty_timetable(client):
    data = client.get("/api/v1/students/me/timetable?week=10", headers={"X-Demo-User":"S2024003"}).json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


def test_course_outline_contains_required_sections(client, student_headers):
    res = client.get("/api/v1/students/me/courses/SE201/outline", headers=student_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["course_name"] == "软件项目管理"
    assert data["teacher"] == "张老师"
    assert data["summary"]
    assert "Scrum" in data["summary"]
    assert data["objectives"] and data["chapters"] and data["assessment"]


def test_student_two_can_view_enrolled_outline(client):
    res = client.get("/api/v1/students/me/courses/SE201/outline", headers={"X-Demo-User":"S2024002"})
    assert res.status_code == 200
    assert res.json()["data"]["course_id"] == "SE201"


def test_service_weekday_names_are_complete():
    assert len(WEEKDAY_NAMES) == 7
    assert WEEKDAY_NAMES[6] == "周日"


def test_service_is_read_only(client):
    """业务层列表查询不更改数据库行数。"""
    with connect(client.app.state.db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
        list_my_courses(conn, "S2024001")
        get_timetable(conn, "S2024001", 1)
        get_course_outline(conn, "S2024001", "SE201")
        after = conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0]
    assert before == after
