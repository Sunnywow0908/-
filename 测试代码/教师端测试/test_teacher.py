"""教师端功能与单元测试：用户故事 US-T01 / US-T02 / US-T03 / US-T04。

演示数据约定：
- T001 教师甲：没有任何授课关系，用于空结果场景；
- T003 张老师：主讲 SE201、协讲 MA101，用于"一位教师承担多门课"；
- T005 赵老师：主讲 AI999，该课程大纲初始为未发布状态。
"""
from contextlib import closing

import pytest

from 功能代码及实际项目文件.教师端.service import (
    OUTLINE_FIELDS,
    WEEKDAY_NAMES,
    get_teaching_outline,
    get_teaching_timetable,
    list_course_students,
    list_teaching_courses,
    publish_outline,
    save_outline_draft,
    unpublish_outline,
)
from 功能代码及实际项目文件.公共基础模块.db import connect


def teacher_headers(teacher_id: str) -> dict[str, str]:
    return {"X-Demo-User": teacher_id}


def make_course_without_outline(client, course_id: str, teacher_id: str) -> None:
    """构造一门尚未编写大纲的课程，用于草稿缺失的分支测试。"""
    with closing(connect(client.app.state.db_path)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO courses(id, name, teacher_name, credits, outline_published)"
                " VALUES (?, ?, ?, ?, 0)",
                (course_id, f"待建设课程{course_id}", "测试教师", 1.0),
            )
            conn.execute(
                "INSERT INTO course_teachers(course_id, teacher_id, duty) VALUES (?, ?, '主讲')",
                (course_id, teacher_id),
            )
            conn.execute(
                "INSERT INTO schedules(course_id, weekday, start_section, end_section,"
                " classroom, start_week, end_week) VALUES (?, 3, 5, 6, '教学楼 D401', 1, 16)",
                (course_id,),
            )


# ---------------------------------------------------------------- US-T01 授课课程

def test_teaching_courses_list(client):
    res = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T003"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] == 2
    assert {item["course_id"] for item in data["items"]} == {"SE201", "MA101"}


def test_teaching_courses_expose_duty_and_counts(client):
    data = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T003")).json()["data"]
    rows = {item["course_id"]: item for item in data["items"]}
    assert rows["SE201"]["duty"] == "主讲"
    assert rows["SE201"]["student_count"] == 2
    assert rows["MA101"]["duty"] == "协讲"
    assert rows["MA101"]["student_count"] == 1
    assert rows["MA101"]["credits"] == 4.0
    assert rows["MA101"]["outline_published"] is True


def test_courses_sorted_by_course_id(client):
    data = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T003")).json()["data"]
    assert [item["course_id"] for item in data["items"]] == ["MA101", "SE201"]


def test_teacher_without_assignment_has_empty_course_list(client):
    data = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T001")).json()["data"]
    assert data == {"total": 0, "items": []}


def test_each_teacher_only_sees_own_courses(client):
    data = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T002")).json()["data"]
    assert [item["course_id"] for item in data["items"]] == ["CS101"]
    assert data["items"][0]["duty"] == "主讲"


def test_co_teacher_and_primary_teacher_share_the_same_course(client):
    primary = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T004")).json()["data"]
    assistant = client.get("/api/v1/teachers/me/courses", headers=teacher_headers("T003")).json()["data"]
    assert primary["items"][0]["course_id"] == "MA101" and primary["items"][0]["duty"] == "主讲"
    assert assistant["items"][0]["course_id"] == "MA101" and assistant["items"][0]["duty"] == "协讲"


# ---------------------------------------------------------------- US-T02 授课课表

def test_teaching_timetable_defaults_to_first_week(client):
    data = client.get("/api/v1/teachers/me/timetable", headers=teacher_headers("T003")).json()["data"]
    assert data["week"] == 1
    assert data["teacher_id"] == "T003"
    assert data["total"] == 2


def test_teaching_timetable_sorted_by_weekday_and_section(client):
    data = client.get("/api/v1/teachers/me/timetable?week=1", headers=teacher_headers("T003")).json()["data"]
    assert [item["course_id"] for item in data["items"]] == ["SE201", "MA101"]
    assert [item["weekday"] for item in data["items"]] == [2, 4]
    assert data["items"][0]["weekday_name"] == "周二"
    assert data["items"][0]["start_section"] == 3
    assert data["items"][0]["end_section"] == 4
    assert data["items"][0]["classroom"] == "教学楼 B202"


def test_teaching_timetable_marks_duty_per_course(client):
    data = client.get("/api/v1/teachers/me/timetable?week=1", headers=teacher_headers("T003")).json()["data"]
    duties = {item["course_id"]: item["duty"] for item in data["items"]}
    assert duties == {"SE201": "主讲", "MA101": "协讲"}


def test_teaching_timetable_excludes_ended_course(client):
    data = client.get("/api/v1/teachers/me/timetable?week=19", headers=teacher_headers("T003")).json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["course_id"] == "MA101"


def test_teaching_timetable_last_week_boundary(client):
    data = client.get("/api/v1/teachers/me/timetable?week=20", headers=teacher_headers("T003")).json()["data"]
    assert [item["course_id"] for item in data["items"]] == ["MA101"]
    assert data["items"][0]["end_week"] == 20


def test_teacher_without_assignment_has_empty_timetable(client):
    data = client.get("/api/v1/teachers/me/timetable?week=10", headers=teacher_headers("T001")).json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


def test_same_course_is_not_repeated_when_teacher_has_two_duties(client):
    """同一排课行无论命中几条授课关系，都只出现一次。"""
    with closing(connect(client.app.state.db_path)) as conn:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO course_teachers(course_id, teacher_id, duty)"
                " VALUES ('SE201', 'T003', '协讲')"
            )
    data = client.get("/api/v1/teachers/me/timetable?week=1", headers=teacher_headers("T003")).json()["data"]
    assert [item["course_id"] for item in data["items"]] == ["SE201", "MA101"]
    # 同一门课同时存在主讲与协讲记录时，按主讲展示。
    assert data["items"][0]["duty"] == "主讲"


# ---------------------------------------------------------------- US-T03 课程名单

def test_course_students_list_is_sorted(client):
    data = client.get(
        "/api/v1/teachers/me/courses/SE201/students", headers=teacher_headers("T003")
    ).json()["data"]
    assert data["course_id"] == "SE201"
    assert data["course_name"] == "软件项目管理"
    assert data["total"] == 2
    assert [row["student_id"] for row in data["items"]] == ["S2024001", "S2024002"]
    assert data["items"][0]["student_name"] == "学生甲"


def test_course_students_with_single_enrollment(client):
    data = client.get(
        "/api/v1/teachers/me/courses/MA101/students", headers=teacher_headers("T003")
    ).json()["data"]
    assert data["total"] == 1
    assert data["items"] == [{"student_id": "S2024001", "student_name": "学生甲"}]


def test_co_teacher_can_see_the_same_roster(client):
    primary = client.get(
        "/api/v1/teachers/me/courses/MA101/students", headers=teacher_headers("T004")
    ).json()["data"]
    assistant = client.get(
        "/api/v1/teachers/me/courses/MA101/students", headers=teacher_headers("T003")
    ).json()["data"]
    assert primary["items"] == assistant["items"]


def test_course_without_enrollment_has_empty_roster(client):
    make_course_without_outline(client, "EMPTY01", "T003")
    data = client.get(
        "/api/v1/teachers/me/courses/EMPTY01/students", headers=teacher_headers("T003")
    ).json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


# ---------------------------------------------------------------- US-T04 教学大纲

def test_teacher_sees_own_unpublished_outline(client):
    data = client.get(
        "/api/v1/teachers/me/courses/AI999/outline", headers=teacher_headers("T005")
    ).json()["data"]
    assert data["outline_published"] is False
    assert data["has_draft"] is True
    assert data["summary"] == "暂未对学生开放的课程大纲。"
    assert data["teacher"] == "赵老师"


def test_outline_without_draft_returns_blank_form(client):
    """尚未编写过大纲时返回空白草稿，教师可以直接开始填写，而不是看到 404。"""
    make_course_without_outline(client, "DRAFT01", "T003")
    data = client.get(
        "/api/v1/teachers/me/courses/DRAFT01/outline", headers=teacher_headers("T003")
    ).json()["data"]
    assert data["has_draft"] is False
    assert data["outline_published"] is False
    assert all(data[field] == "" for field in OUTLINE_FIELDS)


def test_save_draft_updates_existing_outline_in_place(client):
    payload = {
        "summary": "人工智能导论（修订版）",
        "objectives": "了解大模型的基本原理与工程约束。",
        "chapters": "神经网络、Transformer、大模型应用",
        "assessment": "课程论文 50%，答辩 50%",
    }
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline", headers=teacher_headers("T005"), json=payload
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["summary"] == payload["summary"]
    assert data["has_draft"] is True
    assert data["outline_published"] is False
    with closing(connect(client.app.state.db_path)) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM course_outlines WHERE course_id = 'AI999'"
        ).fetchone()[0]
    assert rows == 1


def test_save_draft_creates_outline_for_the_first_time(client):
    make_course_without_outline(client, "DRAFT02", "T003")
    payload = {
        "summary": "新建课程简介",
        "objectives": "新建教学目标",
        "chapters": "新建章节安排",
        "assessment": "新建考核方式",
    }
    res = client.put(
        "/api/v1/teachers/me/courses/DRAFT02/outline", headers=teacher_headers("T003"), json=payload
    )
    assert res.status_code == 200
    assert res.json()["data"]["has_draft"] is True
    assert res.json()["data"]["summary"] == "新建课程简介"


def test_publish_makes_outline_visible_to_students(client):
    res = client.post(
        "/api/v1/teachers/me/courses/AI999/outline/publish", headers=teacher_headers("T005")
    )
    assert res.status_code == 200
    assert res.json()["data"]["outline_published"] is True
    # 同一份数据，学生端应立即可见，体现两端共用同一数据模型。
    student = client.get(
        "/api/v1/students/me/courses/AI999/outline", headers=teacher_headers("S2024001")
    )
    assert student.status_code == 200
    assert student.json()["data"]["summary"] == "暂未对学生开放的课程大纲。"


def test_publish_then_student_reads_updated_content(client):
    headers = teacher_headers("T005")
    client.put(
        "/api/v1/teachers/me/courses/AI999/outline",
        headers=headers,
        json={
            "summary": "大模型工程实践",
            "objectives": "掌握提示工程与评测方法。",
            "chapters": "提示工程、评测体系",
            "assessment": "项目作品",
        },
    )
    client.post("/api/v1/teachers/me/courses/AI999/outline/publish", headers=headers)
    student = client.get(
        "/api/v1/students/me/courses/AI999/outline", headers=teacher_headers("S2024001")
    )
    assert student.json()["data"]["summary"] == "大模型工程实践"


def test_unpublish_returns_course_to_editable_state(client):
    headers = teacher_headers("T005")
    assert client.post("/api/v1/teachers/me/courses/AI999/outline/publish", headers=headers).json()[
        "data"
    ]["outline_published"] is True
    assert client.post("/api/v1/teachers/me/courses/AI999/outline/unpublish", headers=headers).json()[
        "data"
    ]["outline_published"] is False
    res = client.put(
        "/api/v1/teachers/me/courses/AI999/outline",
        headers=headers,
        json={"summary": "a", "objectives": "b", "chapters": "c", "assessment": "d"},
    )
    assert res.status_code == 200


def test_publish_course_list_reflects_new_state(client):
    headers = teacher_headers("T005")
    client.post("/api/v1/teachers/me/courses/AI999/outline/publish", headers=headers)
    courses = client.get("/api/v1/teachers/me/courses", headers=headers).json()["data"]
    assert courses["items"][0]["outline_published"] is True


# ---------------------------------------------------------------- 业务层单元测试

def test_service_weekday_names_are_complete():
    assert len(WEEKDAY_NAMES) == 7
    assert WEEKDAY_NAMES[0] == "周一"
    assert WEEKDAY_NAMES[6] == "周日"


def test_outline_fields_cover_the_four_required_sections():
    assert set(OUTLINE_FIELDS) == {"summary", "objectives", "chapters", "assessment"}


def test_read_only_service_calls_do_not_change_data(client):
    """列表与查看类业务函数不应写库，保证读接口无副作用。"""
    with closing(connect(client.app.state.db_path)) as conn:
        before = (
            conn.execute("SELECT COUNT(*) FROM course_teachers").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM course_outlines").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0],
        )
        list_teaching_courses(conn, "T003")
        get_teaching_timetable(conn, "T003", 1)
        list_course_students(conn, "T003", "SE201")
        get_teaching_outline(conn, "T005", "AI999")
        after = (
            conn.execute("SELECT COUNT(*) FROM course_teachers").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM course_outlines").fetchone()[0],
            conn.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0],
        )
    assert before == after


def test_publish_then_unpublish_round_trip_restores_original_state(client):
    with closing(connect(client.app.state.db_path)) as conn:
        publish_outline(conn, "T005", "AI999")
        assert get_teaching_outline(conn, "T005", "AI999")["outline_published"] is True
        unpublish_outline(conn, "T005", "AI999")
        assert get_teaching_outline(conn, "T005", "AI999")["outline_published"] is False


def test_save_draft_accepts_whitespace_padded_content(client):
    with closing(connect(client.app.state.db_path)) as conn:
        data = save_outline_draft(
            conn,
            "T005",
            "AI999",
            {"summary": " 含空格简介 ", "objectives": "b", "chapters": "c", "assessment": "d"},
        )
    assert data["summary"] == "含空格简介"


@pytest.mark.parametrize("week", [1, 5, 9, 16, 20])
def test_timetable_only_returns_courses_in_that_week(client, week):
    data = client.get(
        f"/api/v1/teachers/me/timetable?week={week}", headers=teacher_headers("T005")
    ).json()["data"]
    # AI999 第 9~16 周开课，其余教学周教师没有授课安排。
    assert data["total"] == (1 if 9 <= week <= 16 else 0)
