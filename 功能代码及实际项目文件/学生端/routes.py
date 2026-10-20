"""学生端 HTTP API：查询个人课表、选修课程和已发布大纲。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from 功能代码及实际项目文件.公共基础模块.auth import require_student
from 功能代码及实际项目文件.公共基础模块.db import get_db
from 功能代码及实际项目文件.公共基础模块.errors import envelope
from .service import get_course_outline, get_timetable, list_my_courses

router = APIRouter()


@router.get("/student", include_in_schema=False)
def student_page() -> FileResponse:
    """返回与 API 同源的静态演示页面，避免跨域配置。"""
    return FileResponse(Path(__file__).with_name("index.html"), media_type="text/html")


@router.get("/api/v1/students/me/courses", tags=["学生端"])
def courses(
    student_id: str = Depends(require_student),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-S01：学生查看本人已选修课程列表。"""
    result = list_my_courses(conn, student_id)
    return envelope("OK", "success", {"total": len(result), "items": result})


@router.get("/api/v1/students/me/timetable", tags=["学生端"])
def timetable(
    week: int = Query(default=1, ge=1, le=20, description="教学周：1~20"),
    student_id: str = Depends(require_student),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-S02：根据教学周查看个人课表。"""
    return envelope("OK", "success", get_timetable(conn, student_id, week))


@router.get("/api/v1/students/me/courses/{course_id}/outline", tags=["学生端"])
def outline(
    course_id: str,
    student_id: str = Depends(require_student),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-S03：仅向已选该课程的学生展示已发布大纲。"""
    return envelope("OK", "success", get_course_outline(conn, student_id, course_id))
