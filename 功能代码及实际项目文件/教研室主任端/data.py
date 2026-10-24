"""主任增量表及虚构数据：复用原教师账号和授课关系，不重新复制课程简介。"""
from contextlib import closing
from pathlib import Path
from 功能代码及实际项目文件.公共基础模块.db import connect


def initialize_director(db_path: Path, *, seed: bool = True) -> None:
    """公共库初始化后调用；不修改原公共表结构，seed=False仅建空表。"""
    with closing(connect(db_path)) as conn, conn:
        conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        if not seed:
            return
        conn.executemany('INSERT OR IGNORE INTO director_departments VALUES (?,?)', [
            ('SE', '软件工程教研室'), ('MA', '数学教研室'), ('EMPTY', '新建教研室')])
        conn.executemany('INSERT OR IGNORE INTO users(id,name,role) VALUES (?,?,?)', [
            ('D002', '主任乙', 'director'), ('D003', '主任丙', 'director')])
        # D001和T001~T005已由公共模块提供；这里只建立明确的演示归属。
        for director_id, department in [('D001','SE'), ('D002','MA'), ('D003','EMPTY')]:
            if conn.execute("SELECT 1 FROM users WHERE id=? AND role='director'", (director_id,)).fetchone():
                conn.execute('INSERT OR IGNORE INTO director_scopes VALUES (?,?)', (director_id,department))
        for teacher_id, department in [('T001','SE'), ('T002','SE'), ('T003','SE'), ('T004','MA'), ('T005','SE')]:
            if conn.execute("SELECT 1 FROM users WHERE id=? AND role='teacher'", (teacher_id,)).fetchone():
                conn.execute('INSERT OR IGNORE INTO teacher_departments VALUES (?,?)', (teacher_id,department))
        for course_id, teaching_class in [('CS101','软件2401'), ('SE201','软件2402'), ('MA101','联合2401'), ('AI999','软件2403')]:
            if conn.execute('SELECT 1 FROM courses WHERE id=?', (course_id,)).fetchone():
                conn.execute('INSERT OR IGNORE INTO course_offerings(course_id,semester,teaching_class) VALUES (?,?,?)',
                             (course_id,'2026-2027-1',teaching_class))
