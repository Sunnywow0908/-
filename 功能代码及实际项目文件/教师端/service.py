"""教师端业务层：授课课程、授课课表、课程名单与教学大纲发布。

与学生端的关键差异：教师的数据可见范围由 course_teachers 授课关系决定，
而不是由学生自己的选课关系决定；所有"按课程 id"的入口都必须先校验授课权限，
对非本人授课的课程统一返回 404，避免通过报错差异探测他人课程。
"""
from __future__ import annotations

import sqlite3

from 功能代码及实际项目文件.公共基础模块.errors import BusinessError


WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

# 大纲四个字段的数据库列名，供草稿保存与空白校验复用。
OUTLINE_FIELDS = ("summary", "objectives", "chapters", "assessment")


def _require_teaching_course(
    conn: sqlite3.Connection, teacher_id: str, course_id: str
) -> sqlite3.Row:
    """校验课程确实由该教师授课；不存在与"别人教的课"返回同一个错误。"""
    row = conn.execute(
        """SELECT c.id, c.name, c.teacher_name, c.credits, c.outline_published,
                  ct.duty, u.name AS teacher_display_name
           FROM course_teachers AS ct
           JOIN courses AS c ON c.id = ct.course_id
           JOIN users AS u ON u.id = ct.teacher_id
           WHERE ct.teacher_id = ? AND ct.course_id = ?""",
        (teacher_id, course_id),
    ).fetchone()
    if row is None:
        raise BusinessError(404, "COURSE_NOT_FOUND", "未找到本人授课的课程")
    return row


def list_teaching_courses(conn: sqlite3.Connection, teacher_id: str) -> list[dict]:
    """US-T01：列出本人承担的全部课程，含授课身份、选课人数与大纲发布状态。"""
    rows = conn.execute(
        """SELECT c.id, c.name, c.teacher_name, c.credits, c.outline_published,
                  ct.duty,
                  (SELECT COUNT(*) FROM enrollments AS e WHERE e.course_id = c.id)
                      AS student_count,
                  (SELECT COUNT(*) FROM schedules AS s WHERE s.course_id = c.id)
                      AS session_count
           FROM course_teachers AS ct
           JOIN courses AS c ON c.id = ct.course_id
           WHERE ct.teacher_id = ?
           ORDER BY c.id""",
        (teacher_id,),
    ).fetchall()
    return [
        {
            "course_id": row["id"],
            "course_name": row["name"],
            "teacher": row["teacher_name"],
            "credits": row["credits"],
            "duty": row["duty"],
            "student_count": row["student_count"],
            "session_count": row["session_count"],
            "outline_published": bool(row["outline_published"]),
        }
        for row in rows
    ]


def get_teaching_timetable(
    conn: sqlite3.Connection, teacher_id: str, week: int
) -> dict:
    """US-T02：按教学周返回本人授课安排。

    一名教师在同一门课中既是主讲又是协讲时，课程内可能出现两条 course_teachers 记录，
    这里按排课行聚合，避免同一节课在课表里出现两次。
    """
    rows = conn.execute(
        """SELECT s.id AS schedule_id, c.id AS course_id, c.name AS course_name,
                  c.credits, s.weekday, s.start_section, s.end_section,
                  s.classroom, s.start_week, s.end_week,
                  MAX(CASE WHEN ct.duty = '主讲' THEN 1 ELSE 0 END) AS has_primary
           FROM schedules AS s
           JOIN courses AS c ON c.id = s.course_id
           JOIN course_teachers AS ct ON ct.course_id = c.id AND ct.teacher_id = ?
           WHERE s.start_week <= ? AND s.end_week >= ?
           GROUP BY s.id
           ORDER BY s.weekday, s.start_section, c.id""",
        (teacher_id, week, week),
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["weekday_name"] = WEEKDAY_NAMES[item["weekday"] - 1]
        item["duty"] = "主讲" if item.pop("has_primary") else "协讲"
        items.append(item)
    return {
        "teacher_id": teacher_id,
        "week": week,
        "total": len(items),
        "items": items,
    }


def list_course_students(
    conn: sqlite3.Connection, teacher_id: str, course_id: str
) -> dict:
    """US-T03：查看本人所授课程的选课名单；先校验授课权限再查询。"""
    course = _require_teaching_course(conn, teacher_id, course_id)
    rows = conn.execute(
        """SELECT u.id AS student_id, u.name AS student_name
           FROM enrollments AS e
           JOIN users AS u ON u.id = e.student_id
           WHERE e.course_id = ?
           ORDER BY u.id""",
        (course_id,),
    ).fetchall()
    return {
        "course_id": course["id"],
        "course_name": course["name"],
        "total": len(rows),
        "items": [
            {"student_id": r["student_id"], "student_name": r["student_name"]}
            for r in rows
        ],
    }


def get_teaching_outline(
    conn: sqlite3.Connection, teacher_id: str, course_id: str
) -> dict:
    """US-T04：教师查看教学大纲草稿。

    与学生端不同：教师可以查看自己课程中尚未发布的大纲（草稿），
    尚未创建过大纲时返回空白草稿而不是 404，便于教师直接开始填写。
    """
    course = _require_teaching_course(conn, teacher_id, course_id)
    outline = conn.execute(
        "SELECT summary, objectives, chapters, assessment FROM course_outlines WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    has_draft = outline is not None
    return {
        "course_id": course["id"],
        "course_name": course["name"],
        "teacher": course["teacher_display_name"],
        "duty": course["duty"],
        "outline_published": bool(course["outline_published"]),
        "has_draft": has_draft,
        "summary": outline["summary"] if has_draft else "",
        "objectives": outline["objectives"] if has_draft else "",
        "chapters": outline["chapters"] if has_draft else "",
        "assessment": outline["assessment"] if has_draft else "",
    }


def save_outline_draft(
    conn: sqlite3.Connection, teacher_id: str, course_id: str, draft: dict
) -> dict:
    """US-T04：保存教学大纲草稿。已发布的大纲被锁定，需先撤回发布再修改。"""
    course = _require_teaching_course(conn, teacher_id, course_id)
    if course["outline_published"]:
        raise BusinessError(409, "OUTLINE_LOCKED", "大纲已发布，请先撤回发布再修改")
    # 在业务层统一去除首尾空白，不依赖路由层的 pydantic 清洗，
    # 避免未来从脚本或其他入口直接调用时写入带空白的大纲。
    values = tuple((draft[field] or "").strip() for field in OUTLINE_FIELDS)
    with conn:
        conn.execute(
            """INSERT INTO course_outlines (course_id, summary, objectives, chapters, assessment)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT (course_id) DO UPDATE SET
                   summary = excluded.summary,
                   objectives = excluded.objectives,
                   chapters = excluded.chapters,
                   assessment = excluded.assessment""",
            (course_id, *values),
        )
    return get_teaching_outline(conn, teacher_id, course_id)


def publish_outline(
    conn: sqlite3.Connection, teacher_id: str, course_id: str
) -> dict:
    """US-T04：发布教学大纲。要求草稿四项内容齐全且当前处于未发布状态。"""
    course = _require_teaching_course(conn, teacher_id, course_id)
    if course["outline_published"]:
        raise BusinessError(409, "OUTLINE_ALREADY_PUBLISHED", "该课程大纲已处于发布状态")
    outline = conn.execute(
        "SELECT summary, objectives, chapters, assessment FROM course_outlines WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    if outline is None or not all(
        (outline[field] or "").strip() for field in OUTLINE_FIELDS
    ):
        raise BusinessError(
            409, "OUTLINE_INCOMPLETE", "请先补全课程简介、教学目标、章节安排与考核方式"
        )
    with conn:
        conn.execute("UPDATE courses SET outline_published = 1 WHERE id = ?", (course_id,))
    return get_teaching_outline(conn, teacher_id, course_id)


def unpublish_outline(
    conn: sqlite3.Connection, teacher_id: str, course_id: str
) -> dict:
    """US-T04：撤回已发布的大纲，使课程回到可编辑的草稿状态。"""
    course = _require_teaching_course(conn, teacher_id, course_id)
    if not course["outline_published"]:
        raise BusinessError(409, "OUTLINE_NOT_PUBLISHED", "该课程大纲当前未发布，无需撤回")
    with conn:
        conn.execute("UPDATE courses SET outline_published = 0 WHERE id = ?", (course_id,))
    return get_teaching_outline(conn, teacher_id, course_id)
