"""教学阶段的演示身份上下文；不是正式认证系统。"""
from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import Depends, Header

from .db import get_db
from .errors import BusinessError


def require_student(
    x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> str:
    """检查模拟用户存在且为学生；正式部署需替换为登录态/token 校验。"""
    return _resolve_demo_role(x_demo_user, conn, "student", "学生")


def require_teacher(
    x_demo_user: Annotated[str | None, Header(alias="X-Demo-User")] = None,
    conn: sqlite3.Connection = Depends(get_db),
) -> str:
    """教师端统一入口守卫；与学生端共用同一套身份与角色判定逻辑。"""
    return _resolve_demo_role(x_demo_user, conn, "teacher", "教师")


def _resolve_demo_role(
    x_demo_user: str | None, conn: sqlite3.Connection, expected_role: str, role_label: str
) -> str:
    """演示身份解析：先判存在、再判角色，错误码保持稳定便于前端与测试复用。"""
    if not x_demo_user:
        raise BusinessError(401, "AUTH_REQUIRED", "请提供演示用户标识 X-Demo-User")

    row = conn.execute("SELECT id, role FROM users WHERE id = ?", (x_demo_user,)).fetchone()
    if row is None:
        raise BusinessError(401, "USER_UNKNOWN", "演示用户不存在")
    if row["role"] != expected_role:
        raise BusinessError(403, "ROLE_FORBIDDEN", f"仅{role_label}身份可访问该功能")
    return str(row["id"])
