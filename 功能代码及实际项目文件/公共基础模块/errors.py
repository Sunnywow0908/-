"""全项目统一错误结构，不暴露内部数据库异常细节。"""
from __future__ import annotations

import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    """可预期业务异常，含 HTTP 状态码及稳定错误码。"""

    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)


def envelope(code: str, message: str, data: object = None) -> dict:
    """统一响应结构；data 缺省时输出 null。"""
    return {"code": code, "message": message, "data": data}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def business_handler(_request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=envelope(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # 参数错误统一显示简短消息，不直接反射攻击性输入。
        return JSONResponse(status_code=422, content=envelope("PARAM_INVALID", "请求参数格式或范围不正确"))

    @app.exception_handler(sqlite3.Error)
    async def database_handler(_request: Request, _exc: sqlite3.Error) -> JSONResponse:
        # 真实应用应记录异常到服务端日志；对客户端隐藏路径和 SQL 细节。
        return JSONResponse(status_code=503, content=envelope("DB_UNAVAILABLE", "数据服务暂不可用"))
