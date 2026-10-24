-- Sprint 1 公共基础数据模型（学生端已交付，教师端在此基础上扩展；
-- 教研室主任端、教学督导端继续复用同一套表结构与统一异常处理）
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'director', 'supervisor'))
);
CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    -- teacher_name 是面向学生的展示名；真正的授课归属以 course_teachers 为准。
    teacher_name TEXT NOT NULL,
    credits REAL NOT NULL CHECK (credits > 0),
    outline_published INTEGER NOT NULL DEFAULT 0 CHECK (outline_published IN (0, 1))
);
-- 教师端新增：教师与课程的授课关系。一门课可有多名教师（主讲/协讲），一名教师可承担多门课。
CREATE TABLE IF NOT EXISTS course_teachers (
    course_id TEXT NOT NULL REFERENCES courses(id),
    teacher_id TEXT NOT NULL REFERENCES users(id),
    duty TEXT NOT NULL DEFAULT '主讲' CHECK (duty IN ('主讲', '协讲')),
    PRIMARY KEY (course_id, teacher_id)
);
CREATE TABLE IF NOT EXISTS enrollments (
    student_id TEXT NOT NULL REFERENCES users(id),
    course_id TEXT NOT NULL REFERENCES courses(id),
    PRIMARY KEY(student_id, course_id)
);
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL REFERENCES courses(id),
    weekday INTEGER NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    start_section INTEGER NOT NULL CHECK (start_section BETWEEN 1 AND 12),
    end_section INTEGER NOT NULL CHECK (end_section BETWEEN start_section AND 12),
    classroom TEXT NOT NULL,
    start_week INTEGER NOT NULL CHECK (start_week BETWEEN 1 AND 20),
    end_week INTEGER NOT NULL CHECK (end_week BETWEEN start_week AND 20),
    UNIQUE(course_id, weekday, start_section, classroom)
);
CREATE TABLE IF NOT EXISTS course_outlines (
    course_id TEXT PRIMARY KEY REFERENCES courses(id),
    summary TEXT NOT NULL,
    objectives TEXT NOT NULL,
    chapters TEXT NOT NULL,
    assessment TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_schedules_course ON schedules(course_id);
CREATE INDEX IF NOT EXISTS idx_course_teachers_teacher ON course_teachers(teacher_id);
