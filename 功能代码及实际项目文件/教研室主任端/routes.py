"""主任端页面与只读API，不提供课程维护及评价录入功能。"""
import sqlite3
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, Query, Path as PathParam
from fastapi.responses import FileResponse
from 功能代码及实际项目文件.公共基础模块.db import get_db
from 功能代码及实际项目文件.公共基础模块.errors import envelope
from 功能代码及实际项目文件.公共基础模块.auth import require_director
from . import service

router = APIRouter()
Identifier = Annotated[str, Query(min_length=1, max_length=32, pattern=r'^[A-Za-z0-9_-]+$')]


@router.get('/director', include_in_schema=False)
def director_page():
    """同源页面，通过公共演示身份请求头调用API。"""
    return FileResponse(Path(__file__).with_name('index.html'), media_type='text/html')


@router.get('/api/v1/directors/me/teachers', tags=['教研室主任端'])
def teachers(user: str = Depends(require_director), conn: sqlite3.Connection = Depends(get_db)):
    items = service.list_teachers(conn, user)
    return envelope('OK', 'success', {'items': items, 'total': len(items)})


@router.get('/api/v1/directors/me/courses', tags=['教研室主任端'])
def courses(teacher_id: Identifier | None = None, user: str = Depends(require_director),
            conn: sqlite3.Connection = Depends(get_db)):
    """US-04：返回当前教研室教师课程简介。"""
    items = service.list_courses(conn, user, teacher_id)
    return envelope('OK', 'success', {'items': items, 'total': len(items)})


@router.get('/api/v1/directors/me/courses/{course_id}/summary', tags=['教研室主任端'])
def summary(course_id: Annotated[str, PathParam(min_length=1, max_length=32, pattern=r'^[A-Za-z0-9_-]+$')],
            user: str = Depends(require_director), conn: sqlite3.Connection = Depends(get_db)):
    return envelope('OK', 'success', service.get_course(conn, user, course_id))


@router.get('/api/v1/directors/me/offerings', tags=['教研室主任端'])
def offerings(teacher_id: Identifier | None = None,
              semester: Annotated[str | None, Query(pattern=r'^\d{4}-\d{4}-[12]$')] = None,
              user: str = Depends(require_director), conn: sqlite3.Connection = Depends(get_db)):
    """US-05：按教师及学期查询本教研室开课情况。"""
    if semester:
        start, end, _ = semester.split('-')
        if int(end) != int(start) + 1:
            from 功能代码及实际项目文件.公共基础模块.errors import BusinessError
            raise BusinessError(422, 'PARAM_INVALID', '学年结束年份必须比开始年份大1')
    items = service.list_offerings(conn, user, teacher_id, semester)
    return envelope('OK', 'success', {'items': items, 'total': len(items)})
