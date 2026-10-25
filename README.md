# Sprint 1 交付：公共基础模块 + 学生端 + 教师端 + 教研室主任端

《软件项目管理》实验二（代号“蜂鸟”）Sprint 1 可运行教学原型。仓库按功能分支交付三个子模块：

- `feature/6a-common-student`：公共基础模块（含测试）与学生端（功能代码 + 单元测试 + 异常场景测试）；
- **`feature/teacher`（本分支）**：教师端（功能代码 + 单元测试 + 异常场景测试），完整复用同一套公共基础模块。
- `feature/director`：教研室主任端（功能代码 + 单元测试 + 异常场景测试），复用公共基础模块及教师授课关系，支持课程简介与开课情况查看。

教学督导端仍由其他成员分工交付，**不在本仓库中冒充已经实现**。

> **需求来源与假设：**指导书要求本轮交付“代码能跑、基本测试、代码注释”，有分支策略、清晰提交记录、README。课程项目选择“爱教学”，学生端按照实验一 Sprint 1 切片中的“查看课表、浏览课程大纲详情”开展实现。仓库中 `US-S01`～`US-S03` 是**本子模块内部标识**，团队集成时需与实验一的真实故事编号对应。

## 1. 功能清单

| 模块 | 交付功能 | 演示与验收方式 |
| --- | --- | --- |
| 公共基础模块 | SQLite 数据表结构、用户角色上下文、演示数据、依赖注入、统一 API 响应与异常处理、数据库健康检查 | `GET /api/v1/health`、公共功能测试 |
| 学生端 US-S01 | 查看本人已选课程列表 | 打开学生端页面，或请求 `/api/v1/students/me/courses` |
| 学生端 US-S02 | 按第 1～20 教学周查看本人课表（星期、节次、教室、授课教师、起止周） | 学生端切换教学周；请求 `/api/v1/students/me/timetable?week=10` |
| 学生端 US-S03 | 查看本人已选修、已发布课程的课程大纲（简介、目标、章节、考核） | 点击“查看大纲”；请求 `/api/v1/students/me/courses/SE201/outline` |
| 异常与边界 | 缺少演示身份、错误角色、身份不存在、课程未选修、课程未发布、周次不合法、SQL 注入式输入、数据库不可用 | `pytest -q 测试代码/异常情况测试` |
| 教师端 US-T01 | 查看本人承担的全部授课课程（授课身份、选课人数、排课次数、大纲发布状态） | 打开教师端页面，或请求 `/api/v1/teachers/me/courses` |
| 教师端 US-T02 | 按第 1～20 教学周查看本人授课安排（星期、节次、教室、起止周、主讲/协讲） | 教师端切换教学周；请求 `/api/v1/teachers/me/timetable?week=10` |
| 教师端 US-T03 | 查看本人所授课程的选课名单 | 点击“名单”；请求 `/api/v1/teachers/me/courses/SE201/students` |
| 教师端 US-T04 | 教学大纲草稿查看、保存、发布与撤回 | 教师端“大纲”面板；请求 `PUT …/outline` 与 `POST …/outline/publish` |
| 教师端异常与边界 | 越权访问他人课程、大纲状态机冲突、请求体字段缺失/空白/超长/类型错误、越权写入无副作用 | `pytest -q 测试代码/异常情况测试` |
| 教研室主任端 US-04 | 查看本教研室教师课程简介，展示教师、课程和主讲/协讲身份，支持按教师筛选 | 打开主任端页面，或请求 `/api/v1/directors/me/courses`；点击“查看简介” |
| 教研室主任端 US-05 | 查看本教研室教师开课情况，展示课程、学期、教学班，支持按教师和学期筛选 | 主任端开课卡片；请求 `/api/v1/directors/me/offerings?semester=2026-2027-1` |
| 教研室主任端异常与边界 | 缺少身份、错误角色、未配置管理范围、跨教研室访问、无效参数、简介缺失或未发布、数据库不可用 | `pytest -q 测试代码/异常情况测试/test_exceptions.py -k director` |

**本项目是教学模拟，不包含正式登录、成绩录入、选课操作或真实个人信息。**当前接口使用 `X-Demo-User` 请求头模拟学生／教师／教研室主任身份；它**不能替代真实身份认证**。后续 Sprint 上线前必须接入会话或 Token 校验及相应权限审计。

教师端的可见范围完全由 `course_teachers` 授课关系决定，而不是由课程上的展示名决定；所有按课程 id 的入口都会先校验授课权限，对他人课程统一返回 404，避免通过报错差异探测。

教研室主任端的可见范围由 `director_scopes` 与 `teacher_departments` 确定，授课关系继续使用 `course_teachers`，简介读取同一份 `course_outlines.summary`。主任管理本教研室教师的主讲和协讲课程；未知与越权教师/课程统一返回 404。主任端只展示已发布简介，缺失或空白时提示“暂无课程简介”，未发布时提示“课程简介尚未发布”。

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
│   ├── 学生端/
│       ├── routes.py        # 学生端 API 和页面入口
│       ├── service.py       # 选课/课表/大纲业务逻辑
│       └── index.html       # 可直接交互的学生端展示界面
│   ├── 教师端/
│       ├── routes.py        # 教师端 API 和页面入口
│       ├── service.py       # 授课课程/课表/名单/大纲发布业务逻辑
│       └── index.html       # 教师教学中心页面（风格与学生端一致）
│   └── 教研室主任端/
│       ├── __init__.py      # 主任端模块
│       ├── routes.py        # 主任端 API 和页面入口
│       ├── service.py       # 教师范围、课程简介与开课查询
│       ├── index.html       # 主任中心页面（沿用学生端、教师端样式）
│       ├── schema.sql       # 教研室、管理范围与学期开课附加表
│       └── data.py          # 主任端附加表及虚构演示数据初始化
├── 测试代码/
│   ├── conftest.py          # pytest 临时数据库夹具
│   ├── 公共功能测试/
│   ├── 学生端测试/
│   ├── 教师端测试/
│   ├── 教研室主任端测试/   # test_director.py：业务单元与正常路径测试
│   └── 异常情况测试/     # test_exceptions.py：保留原测试，并追加主任异常场景
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
- **教师操作页面：** http://127.0.0.1:8000/teacher
- **教研室主任操作页面：** http://127.0.0.1:8000/director
- **交互式接口文档：** http://127.0.0.1:8000/docs
- **数据库健康检查：** http://127.0.0.1:8000/api/v1/health

首次启动会自动建立 `data/sprint1_backup.sqlite3` 并加载**虚构演示数据**。使用 `Ctrl+C` 停止服务。学生端默认“学生甲”，教师端默认“张老师”，均可在右上角切换演示身份与教学周。

主任端默认“主任甲”，可切换主任身份、筛选任课教师和学期；“查看简介”以弹窗展示课程内容。学期仅筛选开课情况，留空查询全部学期。主任端附加表在公共数据库初始化之后自动创建，无需手工删除或修改原数据库。

## 4. 接口与请求示例

| 方法 | 路径 | 用途 | 必需的 Header |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | 公共健康检查 | 无 |
| GET | `/api/v1/students/me/courses` | 查询本人已选课程 | `X-Demo-User: S2024001` |
| GET | `/api/v1/students/me/timetable?week=1` | 查询指定周个人课表 | 同上 |
| GET | `/api/v1/students/me/courses/SE201/outline` | 查询已发布教学大纲 | 同上 |
| GET | `/api/v1/teachers/me/courses` | 查询本人授课课程 | `X-Demo-User: T003` |
| GET | `/api/v1/teachers/me/timetable?week=1` | 查询指定周授课安排 | 同上 |
| GET | `/api/v1/teachers/me/courses/SE201/students` | 查询所授课程名单 | 同上 |
| GET | `/api/v1/teachers/me/courses/AI999/outline` | 查询大纲草稿（未发布也可见） | 同上 |
| PUT | `/api/v1/teachers/me/courses/AI999/outline` | 保存大纲草稿 | 同上 |
| POST | `/api/v1/teachers/me/courses/AI999/outline/publish` | 发布大纲 | 同上 |
| POST | `/api/v1/teachers/me/courses/AI999/outline/unpublish` | 撤回发布 | 同上 |
| GET | `/api/v1/directors/me/teachers` | 查询管理范围内教师，包含未安排授课教师 | `X-Demo-User: D001` |
| GET | `/api/v1/directors/me/courses?teacher_id=T003` | 查询指定教师的课程简介列表 | 同上 |
| GET | `/api/v1/directors/me/courses/CS101/summary` | 查询单门课程简介及管理范围内任课教师 | 同上 |
| GET | `/api/v1/directors/me/offerings?teacher_id=T003&semester=2026-2027-1` | 查询指定教师、学期的开课记录 | 同上 |

例如在终端执行：

```bash
curl -H "X-Demo-User: S2024001" "http://127.0.0.1:8000/api/v1/students/me/timetable?week=10"
```

PowerShell 推荐使用：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/students/me/timetable?week=10" -Headers @{"X-Demo-User"="S2024001"}
```

教师端发布大纲的完整流程（先撤回 → 改草稿 → 再发布）：

```powershell
$h = @{"X-Demo-User"="T005"}
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/teachers/me/courses/AI999/outline/unpublish" -Headers $h
Invoke-RestMethod -Method Put  -Uri "http://127.0.0.1:8000/api/v1/teachers/me/courses/AI999/outline" -Headers $h -ContentType "application/json" -Body '{"summary":"大模型工程实践","objectives":"掌握提示工程","chapters":"提示工程、评测体系","assessment":"项目作品"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/teachers/me/courses/AI999/outline/publish" -Headers $h
```

主任端查询示例：

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/directors/me/offerings?teacher_id=T003&semester=2026-2027-1" -Headers @{"X-Demo-User"="D001"}
```

成功响应采用 `{"code":"OK","message":"success","data":{...}}`，异常响应采用 `{"code":"错误码","message":"提示","data":null}`。

**演示用户**：`S2024001` 有 4 门选修课程，其中 1 门大纲未发布；`S2024002` 只选修 `SE201`；`S2024003` 尚无课程。`D001`（主任）、`V001`（督导）会被学生端与教师端接口同时拒绝（403）。

**演示教师**：`T001` 教师甲本轮未安排授课（空列表场景）；`T002` 李老师主讲 `CS101`；`T003` 张老师主讲 `SE201`、协讲 `MA101`（一人多课场景）；`T004` 王老师主讲 `MA101`；`T005` 赵老师主讲 `AI999`，该课大纲初始未发布，可用于演示发布流程。所有教师身份调用学生端接口都会返回 403。

**演示主任**：`D001` 主任甲负责软件工程教研室，初始显示 4 条教师课程记录与 4 条开课记录；`D002` 主任乙负责数学教研室；`D003` 主任丙负责空教研室。软件工程教师 `T003` 的 `MA101` 协讲记录在主任甲范围内，但数学教师 `T004` 的记录不在主任甲范围内；`T001` 可用于验证无授课记录。学生、教师和督导身份访问主任接口返回 403。数量以初始演示数据为准。

学期示例为 `2026-2027-1`；输入 `2025-2026-2` 可验证空开课列表，输入 `2026-2028-1` 可验证非法学年提示。教师端发布课程简介后，主任端刷新可读取同一份已发布内容。

## 5. 自动化测试

在**项目根目录**执行：

```bash
python -m pytest -q 测试代码
# 可分开查看：
python -m pytest -q 测试代码/公共功能测试
python -m pytest -q 测试代码/学生端测试
python -m pytest -q 测试代码/教师端测试
python -m pytest -q 测试代码/教研室主任端测试
python -m pytest -q 测试代码/异常情况测试
# 只运行主任端异常场景：
python -m pytest -q 测试代码/异常情况测试/test_exceptions.py -k director
```

测试使用 `pytest` + FastAPI `TestClient`，每个用例独立创建临时 SQLite 数据库，运行后不修改 `data/` 中演示数据。当前实测结果参见 [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)。

最近一次本机运行结果为：**全量 222 项通过，其中主任端正常功能与业务单元测试 18 项、主任端异常测试 60 项，合计 78 项**。另有 1 条 Starlette/httpx 依赖弃用提示，不影响测试通过；实际耗时与提示数量以本机运行结果为准。主任异常测试直接写在原 `test_exceptions.py` 中，未另建异常测试文件。

主任端浏览器检查已覆盖身份切换、教师筛选、学期筛选、空数据、权限提示、简介弹窗以及窄屏布局。团队最终人工审查和验收仍需按 `docs/REVIEW_CHECKLIST.md` 实际执行。

## 6. 分支与提交要求（Git）

- `main`：**仅放项目初始骨架**，用作集成基线。
- `feature/6a-common-student`：**6A 功能分支**，交付公共基础模块与学生端。
- `feature/teacher`：**教师端功能分支**（本分支），在 6A 基线上继续演进，每步业务与测试均独立提交。
- `feature/director`：**教研室主任端功能分支**，在已有公共模块、学生端和教师端基础上接入主任模块，业务、测试及文档分次提交。
- 团队审查：从功能分支发起 PR 或合并请求，人工核查 diff 与测试结果，符合 DoD 后再合并到团队 `main`；**本 ZIP 不伪称已完成团队合并/远程推送**。

查看证据：

```bash
git branch -a
git log --all --graph --decorate --oneline
git diff main...feature/6a-common-student --stat
git diff feature/6a-common-student...feature/teacher --stat
git diff feature/teacher...feature/director --stat
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

git switch feature/teacher
git push -u origin feature/teacher

git switch feature/director
git push -u origin feature/director
```

推荐提交到团队仓库 **同一条功能分支**，再由 DRI 组织 review。不要强推 `main`，不要直接将另一个仓库的无关历史覆盖掉。

## 7. DoD 与协作说明

- [x] 已实现可运行的公共基础模块与学生端增量
- [x] 已实现可运行的教师端增量（授课课程、课表、名单、大纲发布）
- [x] 已实现可运行的教研室主任端增量（教师课程简介、开课情况、教师及学期筛选、管理范围校验）
- [x] 已执行自动化测试并通过（详见 `docs/TEST_REPORT.md`）
- [x] 关键函数、数据库脚本及 API 有代码注释
- [x] 已存在真实功能分支及多笔业务、测试、修复提交
- [ ] 人类成员完成最终代码差异审查（需组员实际审查并勾选）
- [ ] 合并入团队项目主干（须团队审核后操作）
- [ ] 推送到团队远程仓库（尚未提供地址/授权）

**AI 互动原始记录应从真实聊天与执行过程如实收集，不得事后虚构时间或审查结果。**本仓库保留真实 Git 日志和测试验证命令，但 Git 提交不是“人类已审查”的证据。

## 8. 后续集成注意

1. 学生端与教师端共用 `users`、`courses`、`course_outlines`、`schedules`、`course_teachers` 和通用异常处理；教研室主任端与教学督导端可继续复用。
2. 教师端新增的 `course_teachers` 表是纯新增结构，旧的 `sprint1.sqlite3` 备份库可直接被 `schema.sql` 的 `CREATE TABLE IF NOT EXISTS` 升级，无需手工迁移。
3. 其他成员合入时，应先统一代码技术栈、数据库设计、接口路径与实验一故事编号；禁止为了合并而覆盖已存在的组内真实代码。
4. 演示数据和认证方式仅供本轮 4 学时教学 Sprint 使用，不代表可投入正式生产。
5. 教研室主任端通过 `main.py` 注册路由并初始化附加表，`auth.py` 追加 `require_director`；新增 `director_departments`、`director_scopes`、`teacher_departments`、`course_offerings`，原公共建表和种子文件保持不变。
6. 主任端按“管理所属教研室教师”限制范围，沿用原教师账号和主讲/协讲关系。当前授课关系没有学期或教学班维度，本轮不声明支持跨学期教师变更、按班分配任课教师；相关扩展需后续明确模型。
7. 主任端的集成约定、审查项与测试结果统一写入原有 `docs/INTEGRATION.md`、`docs/REVIEW_CHECKLIST.md`、`docs/TEST_REPORT.md`，不另设主任端独立文档。

---

## 四端集成版（含教学督导端）

本项目保留原有学生端、教师端、教研室主任端，并新增**教学督导端—查看课程开设情况**。请优先阅读 [`docs/FOUR_PORTAL_DELIVERY.md`](docs/FOUR_PORTAL_DELIVERY.md) 获取四端网址、接口字段、测试说明及Windows运行指引。

- 四端统一入口：`http://127.0.0.1:8000/portal`
- 新增督导端：`http://127.0.0.1:8000/supervisor`
- 督导演示身份：`V001`（请求头 `X-Demo-User`）
- 全量测试：`python -m pytest -q`

新增督导端测试位于 `测试代码/教学督导端测试/test_supervisor.py`。四端共用FastAPI应用和同一SQLite数据模型。

## 教学督导端筛选界面优化（2026-10-21）

- 督导端：`http://127.0.0.1:8000/supervisor`；四端入口：`/portal`。
- 参照教师端重新设计顶部身份选择与刷新操作区域，新增数据库驱动的**开课学期/课程下拉菜单**、教学大纲状态、关键词搜索、快捷状态筛选、详情对话框及CSV导出。
- 筛选选项接口：`GET /api/v1/supervisors/me/offerings/filters`，要求督导身份；原课程查询接口保持兼容。
- 由于本轮用户故事是“查看课程开设情况”，课程本身的修改、排课及大纲发布仍由原有对应业务端负责，未擅自增加督导写权限。
- 自动化测试：`python -m pytest -q`（261项通过，包括新增筛选接口权限和回归测试）。


## 教学督导检查意见（新增）

进入 `/supervisor`，点击课程行的“查看详情”，即可查看教学班信息、历史检查记录并填写检查类型、结论、正文后保存。操作将真实写入共享SQLite数据库中的 `supervisor_inspections` 表，不修改教师发布的课程和教学大纲。

- `GET /api/v1/supervisors/me/offerings/{offering_id}/inspections`：读取指定教学班历史意见。
- `POST /api/v1/supervisors/me/offerings/{offering_id}/inspections`：提交检查意见，请求体 `{"category":"常规检查","conclusion":"正常","content":"课堂教学秩序良好，建议继续保持。"}`。
- 必须携带 `X-Demo-User: V001`；此演示身份**不是生产环境安全认证**，正式上线应改为真实登录与授权。
- 历史意见留存，不提供覆盖或删除接口。数据持久化在数据库中；请注意备份。
- 运行：`python run.py`；测试：`python -m pytest -q 测试代码`。修改后请停止旧服务并从新版目录重新启动。


### 四端演示的督导身份与学期

教学督导端身份下拉框仅提供督导甲(V001)和督导乙(V002)。学生和主任的越权访问由自动化测试模拟，页面不提供其他角色选择。

正常使用 `python run.py` 启动时，会幂等补充以下学期的**模拟**开课教学班：2024-2025-2、2025-2026-1、2025-2026-2、2026-2027-1、2026-2027-2。每个学期均有实际演示开课记录，不是仅添加下拉选项；不会清空已有督导意见。

为保持既有单元测试的固定小数据集，`create_app(临时数据库路径)` 默认不额外插入历史学期；如需测试完整演示数据，请传入 `demo_history=True`。
