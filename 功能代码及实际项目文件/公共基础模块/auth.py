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
    if not x_demo_user:
        raise BusinessError(401, "AUTH_REQUIRED", "请提供演示用户标识 X-Demo-User")

    row = conn.execute("SELECT id, role FROM users WHERE id = ?", (x_demo_user,)).fetchone()
    if row is None:
        raise BusinessError(401, "USER_UNKNOWN", "演示用户不存在")
    if row["role"] != "student":
        raise BusinessError(403, "ROLE_FORBIDDEN", "仅学生身份可访问该功能")
    return str(row["id"])
