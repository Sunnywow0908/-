# Sprint 1 交付：公共基础模块 + 学生端（分工 6A）

《软件项目管理》实验二（代号“蜂鸟”）Sprint 1 可运行教学原型，**仅交付本人负责的 6A 子模块**：公共基础模块（含测试）和学生端（功能代码 + 单元测试 + 异常场景测试）。教师端、教研室主任端、教学督导端由其他成员分工交付，不在本仓库中冒充已经实现。

> **需求来源与假设：**指导书要求本轮交付“代码能跑、基本测试、代码注释”，有分支策略、清晰提交记录、README。课程项目选择“爱教学”，学生端按照实验一 Sprint 1 切片中的“查看课表、浏览课程大纲详情”开展实现。仓库中 `US-S01`～`US-S03` 是**本子模块内部标识**，团队集成时需与实验一的真实故事编号对应。

## 1. 功能清单

| 模块 | 交付功能 | 演示与验收方式 |
| --- | --- | --- |
| 公共基础模块 | SQLite 数据表结构、用户角色上下文、演示数据、依赖注入、统一 API 响应与异常处理、数据库健康检查 | `GET /api/v1/health`、公共功能测试 |
| 学生端 US-S01 | 查看本人已选课程列表 | 打开学生端页面，或请求 `/api/v1/students/me/courses` |
| 学生端 US-S02 | 按第 1～20 教学周查看本人课表（星期、节次、教室、授课教师、起止周） | 学生端切换教学周；请求 `/api/v1/students/me/timetable?week=10` |
| 学生端 US-S03 | 查看本人已选修、已发布课程的课程大纲（简介、目标、章节、考核） | 点击“查看大纲”；请求 `/api/v1/students/me/courses/SE201/outline` |
| 异常与边界 | 缺少演示身份、错误角色、身份不存在、课程未选修、课程未发布、周次不合法、SQL 注入式输入、数据库不可用 | `pytest -q 测试代码/异常情况测试` |

**本项目是教学模拟，不包含正式登录、成绩录入、选课操作或真实个人信息。**当前接口使用 `X-Demo-User` 请求头模拟学生身份；它**不能替代真实身份认证**。后续 Sprint 上线前必须接入会话或 Token 校验及相应权限审计。

## 2. 交付目录

```text
Sprint1_6A_student_core/
├── 功能代码及实际项目文件/
│   ├── 公共基础模块/
│   │   ├── auth.py          # 演示身份和学生角色限制
│   │   ├── config.py        # 数据库配置
│   │   ├── db.py            # 数据库连接、初始化、请求依赖
│   │   ├── errors.py        # 标准响应与统一异常处理
│   │   ├── schema.sql       # 公共数据表
│   │   └── seed.py          # 幂等演示数据
│   └── 学生端/
│       ├── routes.py        # 学生端 API 和页面入口
│       ├── service.py       # 选课/课表/大纲业务逻辑
│       └── index.html       # 可直接交互的学生端展示界面
├── 测试代码/
│   ├── conftest.py          # pytest 临时数据库夹具
│   ├── 公共功能测试/
│   ├── 学生端测试/
│   └── 异常情况测试/
├── docs/
│   ├── REVIEW_CHECKLIST.md # 团队合并前人工审查清单
│   ├── TEST_REPORT.md      # 实测命令和结果
│   └── INTEGRATION.md      # 其他角色端对接与故事边界
├── main.py                 # FastAPI App 工厂和健康检查
├── run.py                  # 运行入口
├── requirements.txt       # Python 依赖
├── .gitignore
├── .env.example
├── README.md
└── .git/                  # 真实仓库（ZIP 内含主线、功能分支与多次提交历史）
```

## 3. 环境要求

- Python 3.10 或更高版本；Git 2.x
- 依赖：FastAPI、Uvicorn、pytest、httpx（版本范围见 `requirements.txt`）
- 数据存储：Python 内置 `sqlite3`，**无需额外安装 MySQL、Redis**
- Windows / macOS / Linux 均可运行；以下命令均从解压后**项目根目录**执行

### 3.1 Windows PowerShell

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py
```

如系统禁止执行 PowerShell 激活脚本，可跳过激活，改用：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

### 3.2 macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

启动成功后访问：

- **学生操作页面：** http://127.0.0.1:8000/student
- **交互式接口文档：** http://127.0.0.1:8000/docs
- **数据库健康检查：** http://127.0.0.1:8000/api/v1/health

首次启动会自动建立 `data/sprint1.sqlite3` 并加载**虚构演示数据**。使用 `Ctrl+C` 停止服务。前端默认“学生甲”，可在右上角切换不同演示身份与教学周。

## 4. 接口与请求示例

| 方法 | 路径 | 用途 | 必需的 Header |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | 公共健康检查 | 无 |
| GET | `/api/v1/students/me/courses` | 查询本人已选课程 | `X-Demo-User: S2024001` |
| GET | `/api/v1/students/me/timetable?week=1` | 查询指定周个人课表 | 同上 |
| GET | `/api/v1/students/me/courses/SE201/outline` | 查询已发布教学大纲 | 同上 |

例如在终端执行：

```bash
curl -H "X-Demo-User: S2024001" "http://127.0.0.1:8000/api/v1/students/me/timetable?week=10"
```

PowerShell 推荐使用：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/students/me/timetable?week=10" -Headers @{"X-Demo-User"="S2024001"}
```

成功响应采用 `{"code":"OK","message":"success","data":{...}}`，异常响应采用 `{"code":"错误码","message":"提示","data":null}`。

**演示用户**：`S2024001` 有 4 门选修课程，其中 1 门大纲未发布；`S2024002` 只选修 `SE201`；`S2024003` 尚无课程。`T001`（教师）、`D001`（主任）、`V001`（督导）会被学生端接口拒绝（403），可用于角色边界演示。

## 5. 自动化测试

在**项目根目录**执行：

```bash
python -m pytest -q 测试代码
# 可分开查看：
python -m pytest -q 测试代码/公共功能测试
python -m pytest -q 测试代码/学生端测试
python -m pytest -q 测试代码/异常情况测试
```

测试使用 `pytest` + FastAPI `TestClient`，每个用例独立创建临时 SQLite 数据库，运行后不修改 `data/` 中演示数据。当前实测结果参见 [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)。

## 6. 分支与提交要求（Git）

- `main`：**仅放项目初始骨架**，用作集成基线。
- `feature/6a-common-student`：**本人的 6A 功能分支**，各次业务/测试/修复均真实执行 `git commit`，保留在 ZIP 的 `.git/` 中。
- 团队审查：从功能分支发起 PR 或合并请求，人工核查 diff 与测试结果，符合 DoD 后再合并到团队 `main`；**本 ZIP 不伪称已完成团队合并/远程推送**。

查看证据：

```bash
git branch -a
git log --all --graph --decorate --oneline
git diff main...feature/6a-common-student --stat
git status
```

### 6.1 推送至团队的远程仓库

目前没有获得团队仓库的远程地址和可用凭据，因此**本地仓库已经建立，但尚未推送远程**。组员解压后在项目根目录执行（替换为**真实仓库 URL**）：

```bash
git switch feature/6a-common-student
git remote add origin https://github.com/你的组织/你的仓库.git
# 如果 origin 已存在，应改为检查 git remote -v，避免直接覆盖
# 如远程仓库已有项目历史，应先与团队沟通如何集成，切忌强推覆盖
git push -u origin feature/6a-common-student
```

推荐提交到团队仓库 **同一条功能分支**，再由 DRI 组织 review。不要强推 `main`，不要直接将另一个仓库的无关历史覆盖掉。

## 7. DoD 与协作说明

- [x] 已实现可运行的公共基础模块与学生端增量
- [x] 已执行自动化测试并通过（详见 `docs/TEST_REPORT.md`）
- [x] 关键函数、数据库脚本及 API 有代码注释
- [x] 已存在真实功能分支及多笔业务、测试、修复提交
- [ ] 人类成员完成最终代码差异审查（需组员实际审查并勾选）
- [ ] 合并入团队项目主干（须团队审核后操作）
- [ ] 推送到团队远程仓库（尚未提供地址/授权）

**AI 互动原始记录应从真实聊天与执行过程如实收集，不得事后虚构时间或审查结果。**本仓库保留真实 Git 日志和测试验证命令，但 Git 提交不是“人类已审查”的证据。

## 8. 后续集成注意

1. 学生端暂时是基于 REST API 的独立最小增量；另外三个角色端可重用 `users`、`courses`、`course_outlines`、`schedules` 和通用异常处理。
2. 其他成员合入时，应先统一代码技术栈、数据库设计、接口路径与实验一故事编号；禁止为了合并而覆盖已存在的组内真实代码。
3. 演示数据和认证方式仅供本轮 4 学时教学 Sprint 使用，不代表可投入正式生产。
