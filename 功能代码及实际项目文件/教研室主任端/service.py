"""主任只读业务：管理范围以教师所属教研室为准，授课以course_teachers为准。"""
import sqlite3
from 功能代码及实际项目文件.公共基础模块.errors import BusinessError

# 用EXISTS支持主任负责多个教研室，避免范围关系导致重复行。
TEACHER_SCOPE = '''EXISTS (
 SELECT 1 FROM teacher_departments td
 JOIN director_scopes ds ON ds.department_id=td.department_id
 WHERE td.teacher_id=u.id AND ds.director_id=?
)'''


def list_teachers(conn: sqlite3.Connection, director_id: str) -> list[dict]:
    """本教研室教师列表，包括尚未安排授课的教师。"""
    return [dict(r) for r in conn.execute('''SELECT u.id AS teacher_id, u.name AS teacher_name
        FROM users u WHERE u.role='teacher' AND ''' + TEACHER_SCOPE + ' ORDER BY u.id', (director_id,))]


def check_teacher(conn: sqlite3.Connection, director_id: str, teacher_id: str | None) -> None:
    """未知与越权教师使用相同404，不泄露其他教研室的教师信息。"""
    if teacher_id is None:
        return
    row = conn.execute("SELECT 1 FROM users u WHERE u.id=? AND u.role='teacher' AND " + TEACHER_SCOPE,
                       (teacher_id, director_id)).fetchone()
    if row is None:
        raise BusinessError(404, 'TEACHER_NOT_FOUND', '未找到管理范围内的教师')


def list_courses(conn: sqlite3.Connection, director_id: str, teacher_id: str | None = None,
                 course_id: str | None = None) -> list[dict]:
    """US-04：按任课教师展示简介，保留主讲/协讲，不泄露未发布草稿。"""
    check_teacher(conn, director_id, teacher_id)
    sql = '''SELECT c.id AS course_id, c.name AS course_name, u.id AS teacher_id,
        u.name AS teacher_name, ct.duty, c.outline_published,
        CASE WHEN c.outline_published=1 THEN o.summary ELSE NULL END AS summary
        FROM course_teachers ct JOIN users u ON u.id=ct.teacher_id
        JOIN courses c ON c.id=ct.course_id
        LEFT JOIN course_outlines o ON o.course_id=c.id
        WHERE u.role='teacher' AND ''' + TEACHER_SCOPE
    args = [director_id]
    if teacher_id is not None:
        sql += ' AND u.id=?'
        args.append(teacher_id)
    if course_id is not None:
        sql += ' AND c.id=?'
        args.append(course_id)
    items = []
    for row in conn.execute(sql + ' ORDER BY u.id,c.id', args):
        item = dict(row)
        item['outline_published'] = bool(item['outline_published'])
        item['summary_available'] = bool(item['summary'] and item['summary'].strip())
        if not item['summary_available']:
            item['summary'] = '暂无课程简介' if item['outline_published'] else '课程简介尚未发布'
        items.append(item)
    return items


def get_course(conn: sqlite3.Connection, director_id: str, course_id: str) -> dict:
    """单门课程简介附管理范围内的任课教师，不返回其他教研室教师。"""
    items = list_courses(conn, director_id, course_id=course_id)
    if not items:
        raise BusinessError(404, 'COURSE_NOT_FOUND', '未找到管理范围内的课程')
    first = items[0]
    return {key:first[key] for key in ['course_id','course_name','outline_published','summary_available','summary']} | {
        'teachers':[{key:i[key] for key in ['teacher_id','teacher_name','duty']} for i in items]}


def list_offerings(conn: sqlite3.Connection, director_id: str,
                   teacher_id: str | None = None, semester: str | None = None) -> list[dict]:
    """US-05：一个教师与一个教学班一行，所有授课关系仍来自公共表。"""
    check_teacher(conn, director_id, teacher_id)
    sql = '''SELECT f.id AS offering_id, c.id AS course_id, c.name AS course_name,
        u.id AS teacher_id, u.name AS teacher_name, ct.duty, f.semester, f.teaching_class
        FROM course_offerings f JOIN courses c ON c.id=f.course_id
        JOIN course_teachers ct ON ct.course_id=c.id JOIN users u ON u.id=ct.teacher_id
        WHERE u.role='teacher' AND ''' + TEACHER_SCOPE
    args = [director_id]
    if teacher_id is not None:
        sql += ' AND u.id=?'
        args.append(teacher_id)
    if semester is not None:
        sql += ' AND f.semester=?'
        args.append(semester)
    return [dict(r) for r in conn.execute(sql + ' ORDER BY f.semester,u.id,c.id,f.id', args)]
