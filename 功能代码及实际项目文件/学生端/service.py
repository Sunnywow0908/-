"""学生端业务层：课表与大纲查询。所有读取都按当前学生选课关系过滤。"""
from __future__ import annotations

import sqlite3

from 功能代码及实际项目文件.公共基础模块.errors import BusinessError


WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def list_my_courses(conn: sqlite3.Connection, student_id: str) -> list[dict]:
    """查询已选课程；返回大纲公开状态供 UI 控制按钮。"""
    rows = conn.execute(
        """SELECT c.id, c.name, c.teacher_name, c.credits, c.outline_published
           FROM courses AS c
           JOIN enrollments AS e ON e.course_id = c.id
           WHERE e.student_id = ?
           ORDER BY c.id""",
        (student_id,),
    ).fetchall()
    return [
        {"course_id": r["id"], "course_name": r["name"],
         "teacher": r["teacher_name"], "credits": r["credits"],
         "outline_published": bool(r["outline_published"])}
        for r in rows
    ]


def get_timetable(conn: sqlite3.Connection, student_id: str, week: int) -> dict:
    """返回所选周的个人课表；课程按星期、开始节次排序。"""
    rows = conn.execute(
        """SELECT c.id AS course_id, c.name AS course_name,
                  c.teacher_name AS teacher, s.weekday, s.start_section,
                  s.end_section, s.classroom, s.start_week, s.end_week
           FROM schedules AS s
           JOIN courses AS c ON c.id = s.course_id
           JOIN enrollments AS e ON e.course_id = c.id
           WHERE e.student_id = ? AND s.start_week <= ? AND s.end_week >= ?
           ORDER BY s.weekday, s.start_section, c.id""",
        (student_id, week, week),
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["weekday_name"] = WEEKDAY_NAMES[item["weekday"] - 1]
        items.append(item)
    return {"student_id": student_id, "week": week, "total": len(items), "items": items}


def get_course_outline(conn: sqlite3.Connection, student_id: str, course_id: str) -> dict:
    """先校验当前学生的选课权限，再校验课程大纲是否已发布。"""
    row = conn.execute(
        """SELECT c.id AS course_id, c.name AS course_name, c.teacher_name AS teacher,
                  c.credits, c.outline_published, o.summary, o.objectives,
                  o.chapters, o.assessment
           FROM courses AS c
           JOIN enrollments AS e ON e.course_id = c.id
           LEFT JOIN course_outlines AS o ON o.course_id = c.id
           WHERE e.student_id = ? AND c.id = ?""",
        (student_id, course_id),
    ).fetchone()
    if row is None:
        # 返回统一的 404，防止旁路探测其他学生的课程信息。
        raise BusinessError(404, "COURSE_NOT_FOUND", "未找到已选修的课程")
    if not row["outline_published"] or row["summary"] is None:
        raise BusinessError(404, "OUTLINE_UNAVAILABLE", "该课程大纲暂未发布")
    return {
        "course_id": row["course_id"], "course_name": row["course_name"],
        "teacher": row["teacher"], "credits": row["credits"],
        "summary": row["summary"], "objectives": row["objectives"],
        "chapters": row["chapters"], "assessment": row["assessment"],
    }
