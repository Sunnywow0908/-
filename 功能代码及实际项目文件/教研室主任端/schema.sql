-- 仅补充主任范围和开课信息；授课关系继续使用公共course_teachers表。
CREATE TABLE IF NOT EXISTS director_departments (
    id TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS director_scopes (
    director_id TEXT NOT NULL REFERENCES users(id),
    department_id TEXT NOT NULL REFERENCES director_departments(id),
    PRIMARY KEY(director_id, department_id)
);
CREATE TABLE IF NOT EXISTS teacher_departments (
    teacher_id TEXT PRIMARY KEY REFERENCES users(id),
    department_id TEXT NOT NULL REFERENCES director_departments(id)
);
CREATE TABLE IF NOT EXISTS course_offerings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL REFERENCES courses(id),
    semester TEXT NOT NULL, teaching_class TEXT NOT NULL,
    UNIQUE(course_id, semester, teaching_class)
);
CREATE INDEX IF NOT EXISTS idx_teacher_departments_department ON teacher_departments(department_id);
CREATE INDEX IF NOT EXISTS idx_course_offerings_course ON course_offerings(course_id);
