"""教学督导全校开课查询。按教学班去重，统计不受多教师关系影响。"""
from __future__ import annotations
import sqlite3


def list_offerings(conn: sqlite3.Connection, *, keyword: str = "", semester: str | None = None,
                   outline_status: str = "all", page: int = 1, page_size: int = 10) -> dict:
    """全校只读开课记录，使用参数化过滤和稳定排序。"""
    filters = []
    args: list[object] = []
    if keyword.strip():
        filters.append("(c.id LIKE ? OR c.name LIKE ? OR f.teaching_class LIKE ?)")
        pattern = "%" + keyword.strip().replace(chr(92), chr(92)*2).replace("%", chr(92)+"%").replace("_", chr(92)+"_") + "%"
        # ESCAPE使用户输入的%和_按普通字符查询而非任意通配符
        filters[-1] = "(c.id LIKE ? ESCAPE '\\' OR c.name LIKE ? ESCAPE '\\' OR f.teaching_class LIKE ? ESCAPE '\\')"
        args.extend([pattern] * 3)
    if semester:
        filters.append("f.semester = ?")
        args.append(semester)
    if outline_status != "all":
        filters.append("c.outline_published = ?")
        args.append(1 if outline_status == "published" else 0)
    where = " WHERE " + " AND ".join(filters) if filters else ""
    joined = " FROM course_offerings f JOIN courses c ON c.id=f.course_id" + where
    total = conn.execute("SELECT COUNT(*)" + joined, args).fetchone()[0]
    # 聚合教师信息时通过相关子查询，不让多教师JOIN扩大开课记录数量。
    rows = conn.execute("""SELECT f.id AS offering_id, c.id AS course_id,
        c.name AS course_name, c.credits, c.outline_published,
        f.semester, f.teaching_class,
        (SELECT GROUP_CONCAT(u.name || '（' || ct.duty || '）', '、')
         FROM course_teachers ct JOIN users u ON u.id=ct.teacher_id
         WHERE ct.course_id=c.id) AS teachers,
        (SELECT COUNT(*) FROM enrollments e WHERE e.course_id=c.id) AS enrolled_count
        """ + joined + " ORDER BY f.semester DESC,c.id,f.id LIMIT ? OFFSET ?",
        [*args,page_size,(page - 1) * page_size]).fetchall()
    items = [dict(r) for r in rows]
    for item in items:
        item["outline_published"] = bool(item["outline_published"])
        item["teachers"] = item["teachers"] or "暂无授课教师"
    stats = conn.execute("""SELECT COUNT(*) AS offerings,
        COUNT(DISTINCT c.id) AS courses,
        COALESCE(SUM(CASE WHEN c.outline_published=1 THEN 1 ELSE 0 END),0) AS published,
        COALESCE(SUM(CASE WHEN c.outline_published=0 THEN 1 ELSE 0 END),0) AS unpublished""" + joined, args).fetchone()
    return {"items":items,"total":total,"page":page,"page_size":page_size,
            "total_pages":(total+page_size-1)//page_size,"stats":dict(stats)}


CATEGORIES = ('常规检查', '教学进度', '教学大纲', '课堂教学', '其他')
CONCLUSIONS = ('正常', '需关注', '待整改')


def create_inspection(conn: sqlite3.Connection, *, offering_id: int, supervisor_id: str,
                      category: str, conclusion: str, content: str) -> dict:
    """写入一条不可覆盖的督导检查意见，目标必须为真实开课教学班。"""
    from 功能代码及实际项目文件.公共基础模块.errors import BusinessError
    if not conn.execute('SELECT 1 FROM course_offerings WHERE id=?', (offering_id,)).fetchone():
        raise BusinessError(404,'OFFERING_NOT_FOUND','开课教学班不存在')
    content=content.strip()
    if category not in CATEGORIES or conclusion not in CONCLUSIONS or not 5 <= len(content) <= 1000:
        raise BusinessError(422,'PARAM_INVALID','检查意见参数不正确（正文5至1000字）')
    with conn:
        cursor=conn.execute('INSERT INTO supervisor_inspections (offering_id,supervisor_id,category,conclusion,content) VALUES (?,?,?,?,?)',
                            (offering_id,supervisor_id,category,conclusion,content))
    return dict(conn.execute('SELECT i.*,u.name AS supervisor_name FROM supervisor_inspections i JOIN users u ON u.id=i.supervisor_id WHERE i.id=?',(cursor.lastrowid,)).fetchone())


def list_inspections(conn: sqlite3.Connection, offering_id: int) -> list[dict]:
    """仅查询指定教学班的检查历史，按最新优先显示。"""
    from 功能代码及实际项目文件.公共基础模块.errors import BusinessError
    if not conn.execute('SELECT 1 FROM course_offerings WHERE id=?',(offering_id,)).fetchone():
        raise BusinessError(404,'OFFERING_NOT_FOUND','开课教学班不存在')
    return [dict(row) for row in conn.execute('SELECT i.*,u.name AS supervisor_name FROM supervisor_inspections i JOIN users u ON u.id=i.supervisor_id WHERE i.offering_id=? ORDER BY i.id DESC',(offering_id,))]
