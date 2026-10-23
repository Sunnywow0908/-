"""教学督导端：查看课程和详情，记录并查询督导意见。"""
from pathlib import Path
import sqlite3
from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from 功能代码及实际项目文件.公共基础模块.auth import require_supervisor
from 功能代码及实际项目文件.公共基础模块.db import get_db
from 功能代码及实际项目文件.公共基础模块.errors import BusinessError, envelope
from .service import list_offerings, create_inspection, list_inspections

router = APIRouter()

@router.get('/supervisor', include_in_schema=False)
def supervisor_page():
    return FileResponse(Path(__file__).with_name('index.html'),media_type='text/html')

@router.get('/api/v1/supervisors/me/offerings',tags=['教学督导端'])
def offerings(keyword: Annotated[str, Query(max_length=80)] = '',
              semester: Annotated[str | None, Query(pattern=r'^\d{4}-\d{4}-[12]$')] = None,
              outline_status: Annotated[str, Query(pattern='^(all|published|unpublished)$')] = 'all',
              page: Annotated[int, Query(ge=1,le=100000)] = 1,
              page_size: Annotated[int, Query(ge=1,le=100)] = 10,
              _user: str = Depends(require_supervisor), conn: sqlite3.Connection = Depends(get_db)):
    """课程开设查询，限制页长以防止超大响应。"""
    if semester:
        start,end,_ = semester.split('-')
        if int(end) != int(start)+1:
            raise BusinessError(422,'PARAM_INVALID','学年结束年份必须比开始年份大1')
    return envelope('OK','success',list_offerings(conn,keyword=keyword,semester=semester,
                outline_status=outline_status,page=page,page_size=page_size))


@router.get('/api/v1/supervisors/me/offerings/filters', tags=['教学督导端'])
def offering_filters(_user: str = Depends(require_supervisor),
                     conn: sqlite3.Connection = Depends(get_db)):
    """从实际开课表生成筛选选项，避免硬编码学期和课程。"""
    semesters = [r[0] for r in conn.execute(
        'SELECT DISTINCT semester FROM course_offerings ORDER BY semester DESC')]
    courses = [dict(r) for r in conn.execute(
        "SELECT DISTINCT c.id, c.name FROM courses c JOIN course_offerings f ON f.course_id=c.id ORDER BY c.id")]
    return envelope('OK', 'success', {'semesters': semesters, 'courses': courses})


class InspectionCreate(BaseModel):
    """检查意见请求模型：长度和类别双重校验。"""
    category: str = Field(min_length=1, max_length=20)
    conclusion: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=5, max_length=1000)


@router.get('/api/v1/supervisors/me/offerings/{offering_id}/inspections',tags=['教学督导端'])
def inspection_history(offering_id: int, _user: str = Depends(require_supervisor),
                       conn: sqlite3.Connection = Depends(get_db)):
    """查看具体教学班的督导意见历史。"""
    return envelope('OK','success',list_inspections(conn,offering_id))


@router.post('/api/v1/supervisors/me/offerings/{offering_id}/inspections',status_code=status.HTTP_201_CREATED,tags=['教学督导端'])
def submit_inspection(offering_id: int, body: InspectionCreate,
                      supervisor_id: str = Depends(require_supervisor),
                      conn: sqlite3.Connection = Depends(get_db)):
    """督导本人发表检查意见；学生、教师、主任均不能写入。"""
    return envelope('OK','检查意见已记录',create_inspection(conn,offering_id=offering_id,
        supervisor_id=supervisor_id,category=body.category,conclusion=body.conclusion,content=body.content))
