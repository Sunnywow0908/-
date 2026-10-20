"""Sprint 1 应用入口：公共模块和学生端的最小可运行增量。"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from 功能代码及实际项目文件.公共基础模块.config import database_path
from 功能代码及实际项目文件.公共基础模块.db import connect, initialize_database
from 功能代码及实际项目文件.公共基础模块.errors import envelope, register_error_handlers


def create_app(db_path: str | Path | None = None, *, seed: bool = True) -> FastAPI:
    """支持测试注入临时数据库，避免污染实际数据。"""
    resolved = Path(db_path).resolve() if db_path is not None else database_path()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_database(resolved, seed=seed)
        yield

    app = FastAPI(title="Sprint 1 教学管理原型（6A）", version="0.1.0", lifespan=lifespan)
    app.state.db_path = resolved
    register_error_handlers(app)

    @app.get("/", include_in_schema=False)
    def home():
        return RedirectResponse(url="/student", status_code=307)

    @app.get("/api/v1/health", tags=["公共基础模块"])
    def health():
        """轻量健康检查，同时验证数据库连接。"""
        with connect(app.state.db_path) as conn:
            conn.execute("SELECT 1").fetchone()
        return envelope("OK", "success", {"service": "sprint1-6a", "database": "ok"})

    # 通过延迟导入保持公共模块与学生端的职责边界清晰。
    from 功能代码及实际项目文件.学生端.routes import router
    app.include_router(router)
    return app


app = create_app()
