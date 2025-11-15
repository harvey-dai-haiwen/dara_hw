# dara_local v2 – Web 前端 PRD（Vite + React）

## 1. 背景与目标

- **项目名称**：`dara_local v2`
- **背景**：当前 `dara_local` 的 Gatsby 前端 + API 设计无法满足实验室实际使用需求，且结构复杂，不易维护。
- **目标**：
  - 用 **Vite + React** 重建 `dara_local` Web 前端。
  - Web 完整覆盖 `notebooks/streamlined_phase_analysis_K2SnTe5.ipynb` 的：
    - Part 1: XRD Pattern and Setup  
    - Part 2: Load CIFs and Phase Search（含结果可视化）
  - 多用户通过网页提交 job，在本地服务器排队执行，结果返回网页：
    - 每个 job 有清晰的状态（PENDING / RUNNING / COMPLETED / FAILED）
    - 结果包括：
      - `solution.visualize()` 的 Plotly 图
      - `extract_phase_info(solution)` 的完整表格（DataFrame 等价）
      - 单个 solution 的 ZIP 报告下载（CSV + HTML + JSON + summary + CIFs）

- **非目标（v2 不做）**：
  - Notebook Part 3（高级精修）不做 Web 化。
  - 用户登录/权限系统：所有用户看到同一全局队列即可。
  - 跨机器分布式计算，仅支持单机 job 队列。

---

## 2. 用户与使用场景

### 2.1 用户角色

- **实验室成员（典型用户）**
  - 上传 XRD pattern → 配置化学系统和数据库 → 提交 job。
  - 在结果页面查看 Phase Search 图和表格，下载报告。
- **维护者**
  - 了解本地 CIF 数据和 index 状态；
  - 主要负责部署/更新，不需要额外 Web 特权。

### 2.2 典型使用流程

1. 打开浏览器访问 `http://localhost:8899/search`（Submit 页面）。
2. 填写：
   - Pattern 文件；
   - Chemical system + required/exclude elements；
   - Instrument parameters；
   - Database / MP 过滤条件；
   - 自己的名字作为 `user`。
3. 点击 Submit，后端创建 job（状态 PENDING），返回 `job_id`。
4. 页面显示 job 创建成功，可点击跳转到：
   - `/results/{job_id}` 查看该任务详情；
   - `/results` 查看所有任务队列。
5. 后端在本地队列中按顺序运行 job：
   - 选取数据库 CIF（prepare_phases_for_dara）
   - Phase Search（search_phases）
   - 生成 Plotly 图 + phase 表格 + 报告文件。
6. 用户在 `/results/{job_id}` 查看：
   - 所有 solutions 的：
     - Plotly 图；
     - phase_info 表格；
     - ZIP 报告下载链接。
   - Job 状态、错误信息（如有）。

---

## 3. 页面与路由设计（Vite + React）

**技术栈**：

- Vite + React（推荐 TypeScript）
- UI 风格**参考原 `src/dara` 的页面布局**（顶部导航 + 主内容区域 + 边栏/卡片），但功能模块全部重新设计。
- Plotly 集成：`react-plotly.js`（或等效封装）。

**路由**：

- `/search` – Submit 页面（核心表单：Part 1 + Part 2）
- `/tutorial` – Tutorial 页面（解释工作流和用法）
- `/results` – 队列列表页面（Q）
- `/results/:jobId` – 单个 job 的详情页面

---

## 4. `/search` – Submit 页面

### 4.1 页面布局

- 布局风格参考原 Dara：
  - 顶部：标题 + 简短描述（“Streamlined XRD Phase Search”）
  - 左侧卡片：**Part 1 – Pattern & Setup**
  - 右侧卡片：**Part 2 – Database & Filters**
  - 底部：User + Submit 按钮区域

### 4.2 表单字段映射 notebook

**Part 1：Pattern & Setup（对应 cells 4–5, 11）**

- **Pattern 文件上传**
  - 字段：`pattern_file`
  - 文件类型：`.xy`, `.xrdml`, `.xye`, `.raw` 等
  - 前端校验：必要字段

- **Chemical system**
  - 字段：
    - `chemical_system`: 文本，例如 `"Y-Mo-O"`
    - `required_elements`: 多选数组（如 `["Y","Mo","O"]`）
    - `exclude_elements`: 多选数组（可为空）
  - 文案提示：
    - chemical_system：使用 `-` 分隔元素
    - required_elements：决定化学系统过滤（包含所有子系统）

- **Instrument 参数**
  - 字段：
    - `wavelength`：
      - 下拉 + 自定义输入：
        - 预设值："Cu", "Co", "Mo"
        - 或输入数字（Å）
    - `instrument_profile`：
      - 下拉选项，至少包含：`"Aeris-fds-Pixcel1d-Medipix3"`
      - 后续可配置更多 profile

**环境与目录**

- 前端不暴露具体路径；后端根据 `chemical_system` 自动创建：
  - `~/Documents/dara_analysis/<ChemicalSystemNoDash>/`
    - `custom_cifs/`
    - `reports/`

---

**Part 2：Database & Phase Selection（对应 cells 7–8）**

- **Database 选择**
  - 字段：`database`（单选）
  - 选项：
    - `"COD"`, `"ICSD"`, `"MP"`, `"NONE"`
- **MP 选项**（仅 database = "MP" 时启用）
  - `mp_experimental_only`: bool
  - `mp_max_e_above_hull`: float（默认 0.1）
- **其它参数**
  - `max_phases`: int（默认 500）
- 前端展示说明：
  - 简要解释 chemical system filter + MP experimental/theory 策略。

---

**User & 提交**

- `user` 字段：
  - 文本输入（名字/缩写）
  - 用于在队列中标识 job 提交者
- 按钮：
  - `Submit`：
    - 调用 `POST /api/jobs`（multipart/form-data）
  - 成功反馈：
    - 显示 `job_id` + 状态 `PENDING`
    - 按钮：
      - “View Job” → `/results/{job_id}`
      - “View Queue” → `/results`

---

## 5. `/tutorial` – Tutorial 页面

- 内容主要解释：
  - Part 1 / Part 2 概念（pattern、chemical system、database 等）
  - 化学系统过滤的行为（unary / binary / ternary 子系统）
  - COD / ICSD / MP 的差异和推荐使用场景
- 可包含静态示例图/表（不需动态交互）。
- 根据: “submit page 和 result page layout 可以参考原本 dara，功能模块不参考”，tutorial 也可以沿用类似排版风格。

---

## 6. `/results` – 队列列表页面（Q）

### 6.1 表格内容

每行代表一个 job：

- `Job ID`（点击进入 `/results/{job_id}`）
- `User`
- `Pattern filename`
- `Database`（COD / ICSD / MP / NONE）
- `Status`（PENDING / RUNNING / COMPLETED / FAILED）
- `Created time`
- `Finished time`（或 `–`）

### 6.2 筛选与刷新

- 筛选：
  - 按 `status` 过滤（多选或单选）
  - 按 `user` 文本过滤（包含匹配）
- 自动刷新：
  - 每 10s 调用 `GET /api/jobs` 更新
  - 手动刷新按钮（立即刷新）

---

## 7. `/results/:jobId` – Job 详情页面

### 7.1 基本信息 & 状态区域

- 显示：
  - Job ID
  - User
  - Pattern 文件名
  - Database
  - chemical_system, required_elements, exclude_elements
  - 状态 + 时间（created / started / finished）
  - 错误信息（如 status=FAILED）

- 诊断信息（来自 XRD pattern check）：
  - 2θ 范围
  - Intensity 范围
  - 点数
  - 三个检查结果（OK/Warning 文本）

### 7.2 Solutions 区域（显示所有 solutions）

- 需求：**显示所有 solution，不加 Top N 限制**（对应 notebook 所有 `search_results`）。
- UI 设计：
  - 列表或 Accordion，每个 solution 为一折叠卡片：
    - 标题：`Solution {index} – Rwp = X.XX% ({num_phases} phases)`
    - 展开时：
      - Plotly 图
      - phase_details 表格
      - 下载 ZIP 按钮

#### 7.2.1 Plotly 图

- 每个 solution 使用：
  - 后端 `solution.visualize()` 的结果（Plotly figure）
  - 后端将 `fig.to_dict()` 序列化返回，前端用 `react-plotly.js` 渲染。
- 图上功能：
  - 标准 Plotly 交互：缩放、平移、hover、legend。

#### 7.2.2 Phase 表格（DataFrame 等价）

- 使用 `extract_phase_info(solution)` 的 **全部字段**：
  - Source
  - Phase Name
  - Formula
  - Space Group
  - SG Number
  - Crystal System
  - a (Å), b (Å), c (Å)
  - α (°), β (°), γ (°)
  - Weight %
- 前端展示：
  - 完整表格，支持：
    - 按列排序（至少按 Formula、Source、Weight%）
    - 简单过滤（可后续扩展）

#### 7.2.3 ZIP 报告下载

- 每个 solution 提供一个下载按钮：
  - “Download report (ZIP)”
- ZIP 中包含：
  - `refinement_plot.html`（interactive plot）
  - `identified_phases.csv`（Phase table）
  - `refinement_stats.json`
  - `summary.txt`
  - `cif_files/` 目录（复制的 CIF 文件集合）

---

## 8. 后端交互（高层协议）

> 详细后端 API PRD 在 backend 文档中描述，这里只约定前端依赖的关键形态。

### 8.1 `POST /api/jobs` – 创建 job

- 请求：multipart/form-data（表单字段同 `/search` 中定义）。
- 响应：
  ```json
  {
    "job_id": "string-uuid",
    "status": "PENDING"
  }
  ```

### 8.2 `GET /api/jobs` – job 列表（队列）

- 查询参数：
  - `status`（可选）
  - `user`（可选）
- 响应：
  ```json
  {
    "jobs": [
      {
        "job_id": "uuid",
        "user": "Alice",
        "pattern_filename": "20231212_YCl3Onepot_1200.xy",
        "database": "ICSD",
        "status": "COMPLETED",
        "num_phases": 194,
        "created_at": "ISO8601",
        "started_at": "ISO8601",
        "finished_at": "ISO8601",
        "error_message": null
      }
    ],
    "total": 1
  }
  ```

### 8.3 `GET /api/jobs/{job_id}` – 单个 job 详情（A 方案）

> 方案 A：一个接口返回 summary + solutions。

- 响应结构示例：
  ```json
  {
    "job": {
      "job_id": "uuid",
      "user": "Alice",
      "pattern_filename": "20231212_YCl3Onepot_1200.xy",
      "database": "ICSD",
      "chemical_system": "Y-Mo-O",
      "required_elements": ["Y", "Mo", "O"],
      "exclude_elements": [],
      "wavelength": "Cu",
      "instrument_profile": "Aeris-fds-Pixcel1d-Medipix3",
      "status": "COMPLETED",
      "created_at": "ISO8601",
      "started_at": "ISO8601",
      "finished_at": "ISO8601",
      "error_message": null
    },
    "diagnostics": {
      "two_theta_min": 5.0,
      "two_theta_max": 90.0,
      "intensity_min": 957.0,
      "intensity_max": 12286.0,
      "num_points": 4305,
      "checks": {
        "intensity": "ok",
        "num_points": "ok",
        "two_theta_range": "ok"
      }
    },
    "solutions": [
      {
        "index": 1,
        "rwp": 6.10,
        "num_phases": 3,
        "plotly_figure": { /* fig.to_dict() */ },
        "phases_table": {
          "columns": ["Source", "Phase Name", "Formula", "..."],
          "rows": [
            {
              "Source": "ICSD",
              "Phase Name": "254378",
              "Formula": "Y5(MoO6)2",
              "Space Group": "Pmmn",
              "SG Number": 59,
              "Crystal System": "orthorhombic",
              "a (Å)": "11.6396",
              "b (Å)": "5.7232",
              "c (Å)": "7.4820",
              "α (°)": "90.00",
              "β (°)": "90.00",
              "γ (°)": "90.00",
              "Weight %": "0.00"
            }
          ]
        },
        "report_zip_url": "/api/jobs/{job_id}/download/1/zip"
      }
    ]
  }
  ```

### 8.4 `GET /api/jobs/{job_id}/download/{solution_index}/zip`

- 下载对应 solution 的 ZIP 报告。
- 前端只需跳转或触发浏览器下载，无需解析内容。

---

## 9. 多用户与队列策略

- 前端只要求用户填入一个 `user` 字段（名字/缩写），不做登录。
- 所有用户都可以在 `/results` 看到所有 job。
- 可选在列表中按 `user` 过滤，但不限制可见性。
- 队列策略：
  - 后端按 `created_at` 顺序执行 job（串行或有限并行）。
  - 状态机：`PENDING` → `RUNNING` → `COMPLETED` / `FAILED`。

---

## 10. 不实现的部分（本 PRD 明确放弃）

- Notebook Part 3（高级精修）Web 化：
  - 不在 v2 实现；
  - 不提供 Web 入口，仅在 notebook 里保留。
- 用户权限、认证：
  - 不区分谁能看哪些 job。
- 任意复杂的可编辑参数界面：
  - Refinement 参数配置（phase_params, refinement_params）不放到 Web。

---

**总结**：本 PRD 定义了 dara_local v2 Web 前端的全部目标、页面、字段与后端交互契约，基于 `streamlined_phase_analysis_K2SnTe5.ipynb` 的 Part 1 + Part 2 行为进行一一映射。
