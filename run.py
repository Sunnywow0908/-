"""简易启动入口：执行 python run.py 后访问 http://127.0.0.1:8000/student。"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
