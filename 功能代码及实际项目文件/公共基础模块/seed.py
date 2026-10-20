"""教学演示数据；生产环境应改为来自真实教务系统的可信数据。"""
from __future__ import annotations

import sqlite3


def seed_demo(conn: sqlite3.Connection) -> None:
    """幂等插入演示用户、课程和排课，便于每位组员快速复现功能。"""
    conn.executemany(
        "INSERT OR IGNORE INTO users(id, name, role) VALUES (?, ?, ?)",
        [
            ("S2024001", "学生甲", "student"),
            ("S2024002", "学生乙", "student"),
            ("S2024003", "学生丙", "student"),  # 未选课：用于空结果测试
            ("T001", "教师甲", "teacher"),
            ("D001", "主任甲", "director"),
            ("V001", "督导甲", "supervisor"),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO courses(id, name, teacher_name, credits, outline_published) VALUES (?, ?, ?, ?, ?)",
        [
            ("CS101", "数据结构", "李老师", 3.0, 1),
            ("SE201", "软件项目管理", "张老师", 2.0, 1),
            ("MA101", "高等数学", "王老师", 4.0, 1),
            ("AI999", "人工智能前沿（未发布大纲）", "赵老师", 1.0, 0),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO enrollments(student_id, course_id) VALUES (?, ?)",
        [
            ("S2024001", "CS101"), ("S2024001", "SE201"),
            ("S2024001", "MA101"), ("S2024001", "AI999"),
            ("S2024002", "SE201"),
        ],
    )
    conn.executemany(
        """INSERT OR IGNORE INTO schedules
           (course_id, weekday, start_section, end_section, classroom, start_week, end_week)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            ("CS101", 1, 1, 2, "教学楼 A101", 1, 16),
            ("SE201", 2, 3, 4, "教学楼 B202", 1, 18),
            ("MA101", 4, 1, 2, "教学楼 A302", 1, 20),
            ("AI999", 5, 7, 8, "教学楼 C105", 9, 16),
        ],
    )
    conn.executemany(
        """INSERT OR IGNORE INTO course_outlines
           (course_id, summary, objectives, chapters, assessment)
           VALUES (?, ?, ?, ?, ?)""",
        [
            ("CS101", "掌握常用数据结构与算法的设计思想。", "理解基本数据结构并能进行复杂度分析。", "线性表、栈与队列、树、图、查找与排序", "平时 40%，期末 60%"),
            ("SE201", "以 Scrum 为主线学习软件项目计划与交付。", "掌握需求拆分、迭代计划、团队协作与验收。", "用户故事、Sprint 计划、敏捷执行、质量管理、回顾", "实验 60%，报告 40%"),
            ("MA101", "微积分基础与应用。", "掌握极限、导数、积分等基本方法。", "函数与极限、微分学、积分学", "平时 30%，期末 70%"),
            ("AI999", "暂未对学生开放的课程大纲。", "了解前沿方法。", "神经网络", "课程论文"),
        ],
    )
