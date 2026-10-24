"""教师端 HTTP API：授课课程、授课课表、课程名单与教学大纲发布流程。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from 功能代码及实际项目文件.公共基础模块.auth import require_teacher
from 功能代码及实际项目文件.公共基础模块.db import get_db
from 功能代码及实际项目文件.公共基础模块.errors import envelope
from .service import (
    get_teaching_outline,
    get_teaching_timetable,
    list_course_students,
    list_teaching_courses,
    publish_outline,
    save_outline_draft,
    unpublish_outline,
)

router = APIRouter()


class OutlineDraft(BaseModel):
    """教学大纲草稿入参；四项内容都必须非空，长度上限用于拦截误粘贴的大段文本。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=500, description="课程简介")
    objectives: str = Field(min_length=1, max_length=500, description="教学目标")
    chapters: str = Field(min_length=1, max_length=1000, description="章节安排")
    assessment: str = Field(min_length=1, max_length=500, description="考核方式")


@router.get("/teacher", include_in_schema=False)
def teacher_page() -> FileResponse:
    """返回与 API 同源的静态演示页面，避免跨域配置。"""
    return FileResponse(Path(__file__).with_name("index.html"), media_type="text/html")


@router.get("/api/v1/teachers/me/courses", tags=["教师端"])
def my_courses(
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T01：教师查看本人承担的授课课程。"""
    items = list_teaching_courses(conn, teacher_id)
    return envelope("OK", "success", {"total": len(items), "items": items})


@router.get("/api/v1/teachers/me/timetable", tags=["教师端"])
def teaching_timetable(
    week: int = Query(default=1, ge=1, le=20, description="教学周：1~20"),
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T02：按教学周查看本人授课安排。"""
    return envelope("OK", "success", get_teaching_timetable(conn, teacher_id, week))


@router.get("/api/v1/teachers/me/courses/{course_id}/students", tags=["教师端"])
def course_students(
    course_id: str,
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T03：教师查看本人所授课程的选课名单。"""
    return envelope("OK", "success", list_course_students(conn, teacher_id, course_id))


@router.get("/api/v1/teachers/me/courses/{course_id}/outline", tags=["教师端"])
def outline_draft(
    course_id: str,
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T04：教师查看教学大纲草稿，未发布时同样可见。"""
    return envelope("OK", "success", get_teaching_outline(conn, teacher_id, course_id))


@router.put("/api/v1/teachers/me/courses/{course_id}/outline", tags=["教师端"])
def update_outline_draft(
    course_id: str,
    draft: OutlineDraft,
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T04：教师保存教学大纲草稿；已发布的大纲需先撤回才能修改。"""
    return envelope(
        "OK", "success", save_outline_draft(conn, teacher_id, course_id, draft.model_dump())
    )


@router.post("/api/v1/teachers/me/courses/{course_id}/outline/publish", tags=["教师端"])
def publish(
    course_id: str,
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T04：教师发布教学大纲，发布后学生端即可查看。"""
    return envelope("OK", "success", publish_outline(conn, teacher_id, course_id))


@router.post("/api/v1/teachers/me/courses/{course_id}/outline/unpublish", tags=["教师端"])
def unpublish(
    course_id: str,
    teacher_id: str = Depends(require_teacher),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """US-T04：教师撤回已发布的大纲，撤回后重新进入可编辑状态。"""
    return envelope("OK", "success", unpublish_outline(conn, teacher_id, course_id))
