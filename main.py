"""Sprint 1 应用入口：公共模块、学生端与教师端的最小可运行增量。"""
from __future__ import annotations

from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from 功能代码及实际项目文件.公共基础模块.config import database_path
from 功能代码及实际项目文件.公共基础模块.db import connect, initialize_database
from 功能代码及实际项目文件.公共基础模块.errors import envelope, register_error_handlers


def create_app(db_path: str | Path | None = None, *, seed: bool = True, demo_history: bool | None = None) -> FastAPI:
    """支持测试注入临时数据库，避免污染实际数据。"""
    resolved = Path(db_path).resolve() if db_path is not None else database_path()
    # 正常运行默认启用多学期演示数据；临时测试数据库保持原基线，可显式启用。
    use_history = (db_path is None) if demo_history is None else demo_history

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        initialize_database(resolved, seed=seed)
        from 功能代码及实际项目文件.教研室主任端.data import initialize_director
        initialize_director(resolved, seed=seed)
        if seed and use_history:
            from 功能代码及实际项目文件.教研室主任端.demo_semesters import seed_extra_semesters
            seed_extra_semesters(resolved)
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
        with closing(connect(app.state.db_path)) as conn:
            conn.execute("SELECT 1").fetchone()
        return envelope("OK", "success", {"service": "sprint1-6a", "database": "ok"})

    # 通过延迟导入保持公共模块与学生端的职责边界清晰。
    from 功能代码及实际项目文件.学生端.routes import router
    app.include_router(router)
    from 功能代码及实际项目文件.教师端.routes import router as teacher_router
    app.include_router(teacher_router)
    from 功能代码及实际项目文件.教研室主任端.routes import router as director_router
    app.include_router(director_router)
    from 功能代码及实际项目文件.教学督导端.routes import router as supervisor_router
    app.include_router(supervisor_router)

    @app.get("/portal", include_in_schema=False)
    def portal():
        from fastapi.responses import HTMLResponse
        return HTMLResponse("""<!doctype html><html lang=zh-CN><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
        <title>爱教学 · 四端工作台</title><style>body{margin:0;background:#f2f5fa;color:#1c2a43;font-family:system-ui,'Microsoft YaHei',sans-serif}header{background:#142b56;color:white;padding:35px max(24px,calc((100vw - 1100px)/2))}main{max-width:1100px;margin:35px auto;padding:0 24px}h1{font-size:27px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:18px}a{display:block;background:white;padding:28px;border:1px solid #dfe6f0;border-radius:16px;text-decoration:none;color:#1c2a43;box-shadow:0 8px 26px #1532510a}a:hover{border-color:#2956ce}strong{font-size:20px}p{color:#63718a;line-height:1.7}span{color:#2956ce}</style>
        <header><small>SPRINT 1 · 教学管理系统</small><h1>爱教学 · 四端工作台</h1>统一服务 · 共用课程数据</header><main><h2>选择业务端</h2><div class=grid>
        <a href=/student><strong>学生端 →</strong><p>查看个人课程及课程资料</p></a>
        <a href=/teacher><strong>教师端 →</strong><p>查看授课信息与课程大纲</p></a>
        <a href=/director><strong>教研室主任端 →</strong><p>查看教师课程和学期开课信息</p></a>
        <a href=/supervisor><strong>教学督导端 →</strong><p>查看全校课程开设情况并记录检查意见</p></a>
        </div><p>统一入口仅用于页面导航，接口通过演示角色身份控制访问。</p></main></html>""")
    return app


app = create_app()
