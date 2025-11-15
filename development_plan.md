# dara_local v2 – Development Plan

本计划基于 `PRD.md`，目标是按模块逐步实现并测试新的 `dara_local v2`：

- 后端：FastAPI + 本地 job 队列 + Phase Search 执行 + 结果/报告生成
- 前端：Vite + React（TS），4 个页面：`/search`, `/tutorial`, `/results`, `/results/:jobId`
- 策略：**一个模块实现 → 一个模块测试**，尽量每一步都可在本地 `uv venv` 环境下独立验证。

## 文档更新与调试约定

- 每个阶段/模块完成后，先按本计划中的“模块测试”步骤在本地运行测试。
- 如果在测试/调试过程中发现需要调整行为、参数或约束：
  - **先修复代码/配置；**
  - 然后同步更新相关文档：
    - `PRD.md`：如果是产品行为/接口约定的变化；
    - `development_plan.md`：如果是开发流程、技术实现细节或测试步骤的变化。
- 调整完成后，建议在 Git 提交信息中注明对应文档已更新（便于回溯）。

---

## 阶段 0：准备与旧实现隔离

### 目标

- 保留旧版 `dara_local` 作为备份。
- 在 `src/` 下创建新的 `dara_local_v2`（名称可调整），未来由 `launch_local_server.py` 指向它。

### 步骤

1. **创建备份分支（手动操作）**
   ```bash
   git branch backup/dara_local_v1
   ```

2. **新后端包结构设计**（不立即创建文件，仅规划）
   计划在 `src/` 中新增：
   - `dara_local_v2/__init__.py`
   - `dara_local_v2/server/app.py` – FastAPI app 创建与静态文件挂载
   - `dara_local_v2/server/api.py` – REST API：jobs 提交、列表、详情、下载
   - `dara_local_v2/server/models.py` – Pydantic 模型（JobIn, JobSummary, JobDetail 等）
   - `dara_local_v2/server/queue.py` – job 队列抽象 & 存储层
   - `dara_local_v2/server/worker.py` – 后台执行逻辑（Phase Search + 结果生成）
   - `dara_local_v2/server/config.py` – server 端配置（端口、路径等）

3. **暂不修改 `launch_local_server.py`**，待后端 MVP 可用后再切换。

### 测试

- 此阶段只做结构规划与新包创建，不涉及运行测试。

---

## 阶段 1：后端 Job 数据模型与存储层（queue + models）

### 目标

- 定义 job 的输入/输出/状态模型。
- 实现最基础的 job 存储与状态管理（先用 SQLite or MontyDB，本地文件）。

### 技术选型

- **存储**：
  - 初版建议使用 SQLite（标准库 `sqlite3` + 简单 DAO）或 MontyDB（已有依赖）。
  - Job 数量有限、结构相对简单，SQLite 足够。

### 模型设计（Python 伪代码）

`dara_local_v2/server/models.py`：

```python
from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobInput(BaseModel):
    user: str
    chemical_system: str
    required_elements: List[str]
    exclude_elements: List[str]
    wavelength: str  # or numeric, 后端内部转
    instrument_profile: str
    database: str  # COD/ICSD/MP/NONE
    mp_experimental_only: bool
    mp_max_e_above_hull: float
    max_phases: int
    pattern_filename: str  # 保存后的文件名


class JobSummary(BaseModel):
    job_id: str
    user: str
    pattern_filename: str
    database: str
    status: JobStatus
    num_phases: int
    created_at: str
    started_at: Optional[str]
    finished_at: Optional[str]
    error_message: Optional[str]


class Diagnostics(BaseModel):
    two_theta_min: float
    two_theta_max: float
    intensity_min: float
    intensity_max: float
    num_points: int
    checks: Dict[str, str]  # intensity/num_points/two_theta_range -> ok/warn


class PhaseTable(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]


class SolutionResult(BaseModel):
    index: int
    rwp: float
    num_phases: int
    plotly_figure: Dict[str, Any]
    phases_table: PhaseTable
    report_zip_url: str


class JobDetail(BaseModel):
    job: JobSummary
    diagnostics: Diagnostics
    solutions: List[SolutionResult]
```

### queue 存储与操作接口（伪代码）

`dara_local_v2/server/queue.py`：

```python
from typing import List, Optional
from .models import JobInput, JobSummary, JobStatus, JobDetail


class JobStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """初始化 SQLite 表结构: jobs, results."""
        ...

    def create_job(self, job_input: JobInput, pattern_path: str) -> str:
        """插入一条 PENDING job，返回 job_id (uuid)。"""
        ...

    def get_job(self, job_id: str) -> Optional[JobSummary]:
        ...

    def list_jobs(self, status: Optional[JobStatus] = None, user: Optional[str] = None) -> List[JobSummary]:
        ...

    def get_next_pending_job(self) -> Optional[JobSummary]:
        """按 created_at 顺序获取下一条 PENDING job，并乐观锁定或立即标记为 RUNNING。"""
        ...

    def update_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None) -> None:
        ...

    def save_job_detail(self, job_id: str, detail: JobDetail) -> None:
        ...

    def load_job_detail(self, job_id: str) -> Optional[JobDetail]:
        ...
```

### 模块测试

- 在本地 uv 环境中编写一个临时测试脚本 `tmp_test_jobstore.py`：

```python
from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.models import JobInput, JobStatus

store = JobStore(db_path="jobs.sqlite")

job_input = JobInput(
    user="test",
    chemical_system="Y-Mo-O",
    required_elements=["Y", "Mo", "O"],
    exclude_elements=[],
    wavelength="Cu",
    instrument_profile="Aeris-fds-Pixcel1d-Medipix3",
    database="ICSD",
    mp_experimental_only=False,
    mp_max_e_above_hull=0.1,
    max_phases=500,
    pattern_filename="dummy.xy",
)

job_id = store.create_job(job_input, pattern_path="/tmp/dummy.xy")
print("job_id", job_id)

summary = store.get_job(job_id)
print(summary)

pending = store.get_next_pending_job()
print("next pending", pending)

store.update_status(job_id, JobStatus.RUNNING)
print(store.get_job(job_id))
```

- 在项目根目录运行：

```bash
uv run python tmp_test_jobstore.py
```

- 预期：至少能完成 job 插入、查询、状态更新，不抛异常。

---

## 阶段 2：后端 Phase Search 执行逻辑（worker）

### 目标

- 将 notebook Part 1/2 的核心逻辑抽取为可重用的 Python 函数。
- 在 worker 中消费队列 job，执行 Phase Search，生成 JobDetail 数据 + 报告文件。

### 技术要点

- 复用现有组件：
  - `scripts/dara_adapter.py` 中的 `prepare_phases_for_dara`
  - `dara.search_phases` / `dara_local.jobs.LocalPhaseSearchMaker`（按需要选用）
  - notebook 内已有的：
    - pattern 诊断（np + matplotlib）
    - `extract_phase_info(solution)`
    - `export_phase_search_report`（用于生成 CSV/HTML/JSON/CIF）
- Worker 需要：
  - 从 `JobStore` 获取下一条 PENDING job
  - 标记为 RUNNING
  - 执行 Phase Search
  - 组织 JobDetail（含 Plotly figure JSON + phase table）
  - 保存 JobDetail + 报告到磁盘
  - 标记为 COMPLETED 或 FAILED

### 核心执行流程（伪代码）

`dara_local_v2/server/worker.py`：

```python
import time
import uuid
from pathlib import Path
from typing import List

from dara import search_phases
from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.models import JobStatus, JobDetail, SolutionResult, Diagnostics, PhaseTable

# 复用/复制 notebook 中的工具函数：
# - extract_phase_info
# - export_phase_search_report
# - pattern diagnostics

class Worker:
    def __init__(self, store: JobStore, repo_root: Path, base_workdir: Path):
        self.store = store
        self.repo_root = repo_root
        self.base_workdir = base_workdir

    def run_forever(self) -> None:
        while True:
            job = self.store.get_next_pending_job()
            if job is None:
                time.sleep(2)
                continue

            try:
                self._process_job(job.job_id)
            except Exception as exc:  # noqa: BLE001
                self.store.update_status(job.job_id, JobStatus.FAILED, error_message=str(exc))

    def _process_job(self, job_id: str) -> None:
        # 1. 标记 RUNNING
        self.store.update_status(job_id, JobStatus.RUNNING)

        # 2. 读取 JobInput, pattern 文件路径
        summary = self.store.get_job(job_id)
        job_input = ...  # 从 DB 中读取或反序列化

        # 3. 设置工作目录（~/Documents/dara_analysis/<ChemicalSystemNoDash>）
        work_dir = self._ensure_workdirs(job_input)

        # 4. pattern 诊断
        diagnostics = self._compute_diagnostics(job_input.pattern_filename)

        # 5. 数据库 & custom CIF 加载 (prepare_phases_for_dara + custom_cifs)
        all_cif_paths = self._load_cif_paths(job_input)

        # 6. Phase Search（search_phases）
        search_results = search_phases(
            pattern_path=...,  # 绝对路径
            phases=all_cif_paths,
            wavelength=job_input.wavelength,
            instrument_profile=job_input.instrument_profile,
        )

        # 7. 对每个 solution 构建 SolutionResult
        solutions: List[SolutionResult] = []
        for idx, solution in enumerate(search_results, start=1):
            fig = solution.visualize()
            fig_dict = fig.to_dict()

            phase_df = extract_phase_info(solution)  # Pandas DataFrame
            phases_table = PhaseTable(
                columns=list(phase_df.columns),
                rows=phase_df.to_dict(orient="records"),
            )

            # 调用 export_phase_search_report 生成报告目录 & 文件
            report_dir = export_phase_search_report(solution, idx, work_dir / "reports")

            # 生成 ZIP 文件
            zip_path = self._make_zip(report_dir)
            report_zip_url = f"/api/jobs/{job_id}/download/{idx}/zip"

            solutions.append(
                SolutionResult(
                    index=idx,
                    rwp=float(solution.refinement_result.lst_data.rwp),
                    num_phases=len(solution.phases),
                    plotly_figure=fig_dict,
                    phases_table=phases_table,
                    report_zip_url=report_zip_url,
                )
            )

        # 8. 组装 JobDetail 并保存
        detail = JobDetail(
            job=summary,
            diagnostics=diagnostics,
            solutions=solutions,
        )
        self.store.save_job_detail(job_id, detail)

        # 9. 标记 COMPLETED
        self.store.update_status(job_id, JobStatus.COMPLETED)
```

### 模块测试

- 写一个 `tmp_run_single_job.py`，构造一个 fake job，并直接调用 `_process_job(job_id)`：

```python
from pathlib import Path
from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.worker import Worker

store = JobStore("jobs.sqlite")
# 先用阶段 1 的测试脚本创建一个 job，并确保 pattern 文件存在

worker = Worker(store, repo_root=Path.cwd(), base_workdir=Path.home() / "Documents" / "dara_analysis")
worker._process_job(job_id="<填入前面创建的 job_id>")
```

- 预期：运行后：
  - job 状态变为 COMPLETED
  - JobDetail 可从 `store.load_job_detail(job_id)` 读出
  - 工作目录下生成 reports/solution_X/* 和 zip

---

## 阶段 3：后端 FastAPI app & API endpoint

### 目标

- 提供与 PRD 一致的 API：
  - `POST /api/jobs`
  - `GET /api/jobs`
  - `GET /api/jobs/{job_id}`
  - `GET /api/jobs/{job_id}/download/{solution_index}/zip`
- 将 worker 进程加入 FastAPI lifespan，启动时自动运行队列。

### app 结构与伪代码

`dara_local_v2/server/app.py`：

```python
import multiprocessing
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dara_local_v2.server.api import router as api_router
from dara_local_v2.server.queue import JobStore
from dara_local_v2.server.worker import Worker


_repo_root = Path(__file__).resolve().parents[3]
_frontend_dir = _repo_root / "src" / "dara_local_v2" / "ui" / "dist"  # Vite build 输出

_job_store = JobStore(db_path=str(_repo_root / "worker_db" / "jobs.sqlite"))
_worker_process: multiprocessing.Process | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_process  # noqa: PLW0603

    def _worker_target():
        worker = Worker(
            store=_job_store,
            repo_root=_repo_root,
            base_workdir=Path.home() / "Documents" / "dara_analysis",
        )
        worker.run_forever()

    _worker_process = multiprocessing.Process(target=_worker_target, daemon=True)
    _worker_process.start()
    try:
        yield
    finally:
        if _worker_process and _worker_process.is_alive():
            _worker_process.terminate()


app = FastAPI(lifespan=lifespan)

# 注册 API
app.include_router(api_router, prefix="/api")

# 静态前端（Vite 构建产物）
app.mount("", StaticFiles(directory=_frontend_dir.as_posix(), html=True), name="frontend")


def launch_app():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8899, workers=1, timeout_graceful_shutdown=1)
```

`dara_local_v2/server/api.py`：

```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Annotated
from pathlib import Path
import json

from .queue import JobStore
from .models import JobInput, JobStatus

router = APIRouter()
store = ...  # 与 app 中同一个 JobStore 实例


@router.post("/jobs")
async def create_job(
    pattern_file: Annotated[UploadFile, File()],
    user: Annotated[str, Form()],
    chemical_system: Annotated[str, Form()],
    required_elements: Annotated[str, Form()],  # JSON list
    exclude_elements: Annotated[str, Form()],
    wavelength: Annotated[str, Form()],
    instrument_profile: Annotated[str, Form()],
    database: Annotated[str, Form()],
    mp_experimental_only: Annotated[bool, Form()] = False,
    mp_max_e_above_hull: Annotated[float, Form()] = 0.1,
    max_phases: Annotated[int, Form()] = 500,
):
    try:
        required = json.loads(required_elements)
        excluded = json.loads(exclude_elements)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid element lists: {exc}")

    # 保存 pattern 文件到专门目录
    uploads_base = Path.home() / ".dara-local-v2" / "uploads"
    uploads_base.mkdir(parents=True, exist_ok=True)
    pattern_path = uploads_base / pattern_file.filename
    with open(pattern_path, "wb") as f:
        f.write(await pattern_file.read())

    job_input = JobInput(
        user=user,
        chemical_system=chemical_system,
        required_elements=required,
        exclude_elements=excluded,
        wavelength=wavelength,
        instrument_profile=instrument_profile,
        database=database,
        mp_experimental_only=mp_experimental_only,
        mp_max_e_above_hull=mp_max_e_above_hull,
        max_phases=max_phases,
        pattern_filename=pattern_path.name,
    )

    job_id = store.create_job(job_input, pattern_path=str(pattern_path))

    return {"job_id": job_id, "status": JobStatus.PENDING}
```

> 其它 API (`GET /api/jobs`, `GET /api/jobs/{job_id}`, 下载 zip) 按 PRD 中定义的 JSON 结构实现。

### 模块测试

- 启动 app：

```bash
uv run python -c "from dara_local_v2.server.app import launch_app; launch_app()"
```

- 使用 `curl` 或 `httpie` 测试：

```bash
http -f POST http://127.0.0.1:8899/api/jobs \
    user=test \
    chemical_system=Y-Mo-O \
    required_elements='["Y","Mo","O"]' \
    exclude_elements='[]' \
    wavelength=Cu \
    instrument_profile=Aeris-fds-Pixcel1d-Medipix3 \
    database=ICSD \
    mp_experimental_only:=false \
    mp_max_e_above_hull:=0.1 \
    max_phases:=200 \
    pattern_file@path/to/test.xy

http GET http://127.0.0.1:8899/api/jobs
http GET http://127.0.0.1:8899/api/jobs/<job_id>
```

- 检查返回 JSON 是否符合 PRD 要求，状态是否从 PENDING → RUNNING → COMPLETED。

---

## 阶段 4：前端 Vite + React 项目初始化

### 目标

- 在 `src/dara_local_v2/ui` 下初始化 Vite+React 项目（TS）。
- 配置构建输出到 `dist/`，被 FastAPI 作为静态资源挂载。

### 步骤

1. 在 `src/dara_local_v2` 下创建 `ui` 目录：

```bash
cd src/dara_local_v2
npm create vite@latest ui -- --template react-ts
cd ui
npm install
```

2. 调整 Vite 配置（`vite.config.ts`）：

- 设置 `build.outDir = "dist"`（默认即为 dist）
- 如果需要，将 `base` 设为 `/`，确保与 FastAPI 挂载兼容。

3. 确认 `npm run dev` 在 `src/dara_local_v2/ui` 下能启动开发服务器（只用于前端开发时）。

### 模块测试

- 在 `src/dara_local_v2/ui`：

```bash
npm run dev
```

- 浏览器访问 Vite dev 端口（默认 5173）确认初始 React 页面正常。

> 注意：FastAPI 挂载的是 build 后的 `dist`，开发时用 Vite dev server，集成时用 `npm run build` + FastAPI。

---

## 阶段 5：前端路由与页面骨架

### 目标

- 实现 4 条路由：`/search`, `/tutorial`, `/results`, `/results/:jobId`。
- 每个页面先实现布局骨架（标题、主要区域/卡片），不接 API。

### 技术点

- 使用 React Router（如 `react-router-dom`）。

### 伪代码

`src/dara_local_v2/ui/src/main.tsx`：

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { SearchPage } from "./pages/SearchPage";
import { TutorialPage } from "./pages/TutorialPage";
import { ResultsPage } from "./pages/ResultsPage";
import { JobDetailPage } from "./pages/JobDetailPage";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/search" element={<SearchPage />} />
        <Route path="/tutorial" element={<TutorialPage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/results/:jobId" element={<JobDetailPage />} />
        {/* 默认重定向到 /search 或简单首页 */}
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
```

各页面先写简单骨架：

```tsx
// SearchPage.tsx
export function SearchPage() {
  return (
    <div className="page search-page">
      <header>Streamlined XRD Phase Search</header>
      <main>
        <section>{/* 左侧 Part 1 */}</section>
        <section>{/* 右侧 Part 2 */}</section>
      </main>
    </div>
  );
}
```

### 模块测试

- `npm run dev`，手动访问 4 个路由，确保 Router 正常工作，基本布局存在。

---

## 阶段 6：前端 `/search` 表单与 `POST /api/jobs` 集成

### 目标

- 完成 `SearchPage` 表单组件，实现与后端 `POST /api/jobs` 的集成。
- 提交成功后展示 job_id，提供跳转到 `/results/{jobId}` 和 `/results`。

### 技术点

- 使用 `fetch` 或 `axios` 发起 multipart/form-data 请求。
- 表单状态管理可以用 React hooks。

### 伪代码

```tsx
import { useState } from "react";

export function SearchPage() {
  const [user, setUser] = useState("");
  const [chemicalSystem, setChemicalSystem] = useState("Y-Mo-O");
  const [requiredElements, setRequiredElements] = useState<string[]>(["Y", "Mo", "O"]);
  const [excludeElements, setExcludeElements] = useState<string[]>([]);
  const [database, setDatabase] = useState("ICSD");
  const [wavelength, setWavelength] = useState("Cu");
  const [instrumentProfile, setInstrumentProfile] = useState("Aeris-fds-Pixcel1d-Medipix3");
  const [mpExperimentalOnly, setMpExperimentalOnly] = useState(false);
  const [mpMaxEAboveHull, setMpMaxEAboveHull] = useState(0.1);
  const [maxPhases, setMaxPhases] = useState(500);
  const [patternFile, setPatternFile] = useState<File | null>(null);
  const [submitResult, setSubmitResult] = useState<{ job_id: string; status: string } | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!patternFile) return;

    const form = new FormData();
    form.append("pattern_file", patternFile);
    form.append("user", user);
    form.append("chemical_system", chemicalSystem);
    form.append("required_elements", JSON.stringify(requiredElements));
    form.append("exclude_elements", JSON.stringify(excludeElements));
    form.append("wavelength", wavelength);
    form.append("instrument_profile", instrumentProfile);
    form.append("database", database);
    form.append("mp_experimental_only", String(mpExperimentalOnly));
    form.append("mp_max_e_above_hull", String(mpMaxEAboveHull));
    form.append("max_phases", String(maxPhases));

    const res = await fetch("/api/jobs", {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      // 错误处理
      return;
    }
    const data = await res.json();
    setSubmitResult(data);
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* 各种输入控件 */}
      <input type="file" onChange={e => setPatternFile(e.target.files?.[0] ?? null)} />
      {/* user, chemical system, etc. */}
      <button type="submit">Submit</button>

      {submitResult && (
        <div>
          Job created: {submitResult.job_id} ({submitResult.status})
          {/* 链接到 /results/{job_id} 和 /results */}
        </div>
      )}
    </form>
  );
}
```

### 模块测试

- 启动 FastAPI app + Vite build 版本，或者在 dev 模式下设置代理到 `/api`。
- 用真实 XRD pattern 文件提交，检查后端是否收到请求并创建 job。

---

## 阶段 7：前端 `/results` 列表与 `GET /api/jobs` 集成

### 目标

- 实现队列列表页：从 `GET /api/jobs` 读取 job 列表，显示表格。
- 加入按 status/user 筛选和自动轮询刷新。

### 伪代码

```tsx
import { useEffect, useState } from "react";

interface JobSummaryDto {
  job_id: string;
  user: string;
  pattern_filename: string;
  database: string;
  status: string;
  created_at: string;
  finished_at: string | null;
}

export function ResultsPage() {
  const [jobs, setJobs] = useState<JobSummaryDto[]>([]);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [userFilter, setUserFilter] = useState<string>("");

  async function fetchJobs() {
    const params = new URLSearchParams();
    if (statusFilter) params.append("status", statusFilter);
    if (userFilter) params.append("user", userFilter);

    const res = await fetch(`/api/jobs?${params.toString()}`);
    const data = await res.json();
    setJobs(data.jobs);
  }

  useEffect(() => {
    fetchJobs();
    const id = setInterval(fetchJobs, 10000);
    return () => clearInterval(id);
  }, [statusFilter, userFilter]);

  return (
    <div>
      {/* 筛选控件 */}
      <table>
        <thead>...</thead>
        <tbody>
          {jobs.map(job => (
            <tr key={job.job_id}>
              <td><a href={`/results/${job.job_id}`}>{job.job_id}</a></td>
              <td>{job.user}</td>
              <td>{job.pattern_filename}</td>
              <td>{job.database}</td>
              <td>{job.status}</td>
              <td>{job.created_at}</td>
              <td>{job.finished_at ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

### 模块测试

- 后端已有多个 job（可以通过 `/search` 或手动插入）。
- 确认列表正确显示，过滤与自动刷新按预期工作。

---

## 阶段 8：前端 `/results/:jobId` 详情页与 Plotly + 表格集成

### 目标

- 从 `GET /api/jobs/{job_id}` 获取 JobDetail。
- 对每个 solution：显示 Plotly 图 + phase 表格 + 下载 ZIP 按钮。

### 技术点

- 使用 `react-plotly.js` 渲染 `plotly_figure`。
- phase 表格可以用普通 `<table>` 或简单表格组件。

### 伪代码

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Plot from "react-plotly.js";

interface PhaseTableDto {
  columns: string[];
  rows: Record<string, any>[];
}

interface SolutionDto {
  index: number;
  rwp: number;
  num_phases: number;
  plotly_figure: any;
  phases_table: PhaseTableDto;
  report_zip_url: string;
}

interface JobDetailDto {
  job: any;
  diagnostics: any;
  solutions: SolutionDto[];
}

export function JobDetailPage() {
  const { jobId } = useParams();
  const [detail, setDetail] = useState<JobDetailDto | null>(null);

  useEffect(() => {
    async function fetchDetail() {
      const res = await fetch(`/api/jobs/${jobId}`);
      const data = await res.json();
      setDetail(data);
    }
    fetchDetail();
    const id = setInterval(fetchDetail, 10000);
    return () => clearInterval(id);
  }, [jobId]);

  if (!detail) return <div>Loading...</div>;

  return (
    <div>
      {/* Job 基本信息 + diagnostics */}
      {detail.solutions.map(sol => (
        <section key={sol.index}>
          <h2>
            Solution {sol.index} – Rwp = {sol.rwp.toFixed(2)}% ({sol.num_phases} phases)
          </h2>
          <Plot data={sol.plotly_figure.data} layout={sol.plotly_figure.layout} />

          <table>
            <thead>
              <tr>
                {sol.phases_table.columns.map(col => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sol.phases_table.rows.map((row, idx) => (
                <tr key={idx}>
                  {sol.phases_table.columns.map(col => (
                    <td key={col}>{String(row[col])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <button onClick={() => (window.location.href = sol.report_zip_url)}>
            Download report (ZIP)
          </button>
        </section>
      ))}
    </div>
  );
}
```

### 模块测试

- 用一两个完成的 job，访问 `/results/{jobId}`，检查：
  - Plotly 图正常显示、可交互。
  - phase 表格显示所有列。
  - 点击下载按钮能正确下载 ZIP，ZIP 内容符合预期。

---

## 阶段 9：Tutorial 页面与样式优化

### 目标

- 根据 PRD 中描述，填充 `/tutorial` 文案与静态内容。
- 对 `/search` 与 `/results` 页的布局和样式进行优化，使之更接近原 Dara 的风格（但功能保持本 PRD）。

### 步骤

- 编写 `TutorialPage`，以 Markdown/静态 HTML 形式描述：
  - Part 1/Part 2 概念
  - 化学系统过滤逻辑
  - 数据库选择建议
- 添加基本 CSS 或使用简单 UI 库（如 Tailwind 或轻量组件库），保持简洁。

### 模块测试

- 手动浏览 `/tutorial` 与其他页面，检查文案与布局。

---

## 阶段 10：集成测试与回归（对比 notebook）

### 目标

- 使用 `streamlined_phase_analysis_K2SnTe5.ipynb` 作为“金标准”。
- 在相同 pattern + database + 参数下，比较 Web 和 notebook 的结果一致性。

### 步骤

1. 选定一个 pattern（例如 `20231212_YCl3Onepot_1200.xy`）和数据库/参数（ICSD, required_elements = [Y, Mo, O] 等）。
2. 在 notebook 中运行 Part 1 + Part 2，记录：
   - Phase 数量
   - Solutions 数量
   - 每个 solution 的 Rwp
   - phase 表格内容（前几行即可）
3. 在 Web 中通过 `/search` 提交相同参数：
   - 等待 job 完成，通过 `/results/{jobId}` 查看：
     - Phase 数量
     - Solutions 数量
     - Rwp 值
     - phase 表格前几行
4. 对比：
   - 如果差异大，检查：
     - CIF 路径、index 是否一致
     - `prepare_phases_for_dara` 调用参数是否完全一致
     - `search_phases` 参数是否一致

### 模块测试

- 记录至少 1–2 个 case 的对比结果，确保误差仅来自数值细节，而不是逻辑差异。

---

## 阶段 11：切换 `launch_local_server.py` 到新实现

### 目标

- 让根目录的 `launch_local_server.py` 指向 `dara_local_v2.server.app.launch_app`。

### 步骤

1. 修改 `launch_local_server.py`：

```python
# from dara_local.server.app import launch_app
from dara_local_v2.server.app import launch_app
```

2. 重新构建前端：

```bash
cd src/dara_local_v2/ui
npm run build
cd ../../../..
```

3. 启动 server：

```bash
uv run python launch_local_server.py
```

4. 浏览器访问：
   - `http://localhost:8899/search`
   - `http://localhost:8899/results`

### 模块测试

- 完整跑一遍典型流程（提交 → 队列 → 详情 → 下载 ZIP）。

---

## 结束语

以上开发计划将 `dara_local v2` 拆解为多个可独立测试的模块，从后端 job 模型、队列与 Phase Search，到 FastAPI API，再到 Vite+React 前端逐步接入。每个阶段都可以在本地 `uv venv` 环境中运行脚本或前后端服务，确保在集成之前各模块自身稳定可靠。
