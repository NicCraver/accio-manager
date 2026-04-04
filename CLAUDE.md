# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Accio 是一个基于 FastAPI 的多账号管理面板，充当 Anthropic / OpenAI / Gemini API 的本地代理网关。核心功能：多账号管理、额度自动巡检、API 请求调度（轮询/优先填充）、兼容多家 API 格式。

## Common Commands

```bash
# 安装依赖
uv sync

# 启动开发服务器 (端口 4097)
uv run accio-panel
# 或
uv run python main.py

# 运行全部测试
uv run python -m unittest

# 运行单个测试模块
uv run python -m unittest tests.test_runtime_storage
uv run python -m unittest tests.test_release_build

# 本地 Nuitka 单文件构建
uv run --with "nuitka[onefile]==4.0" python -m nuitka --onefile --include-package-data=accio_panel main.py

# 发布：推送版本标签触发 GitHub Actions 构建
git tag v0.1.3
git push origin v0.1.3
```

## Architecture

### 入口与启动

- `main.py` → 导入 `accio_panel.web:run` 启动 Uvicorn
- `pyproject.toml` 定义 CLI 入口 `accio-panel` 指向同一函数
- 版本号由 `hatch-vcs` 从 git tag 自动生成

### 核心模块 (`accio_panel/`)

**Web 层**
- `web.py` — FastAPI 主应用，包含所有路由、会话中间件、模板渲染、后台调度器
- `templates/` — Jinja2 模板（dashboard、oauth、settings 等）

**API 代理层** — 三个独立模块，各自负责请求/响应格式转换：
- `anthropic_proxy.py` — `/v1/models`, `/v1/messages`
- `openai_proxy.py` — `/v1/models`, `/v1/chat/completions`, `/v1/responses`
- `gemini_proxy.py` — `/v1beta/models`, `/v1beta/models/{model}:generateContent`

**存储层** — Repository 模式 + Factory 模式：
- `store.py` — `BaseAccountStore` 抽象基类 + `AccountStore` 文件后端实现
- `mysql_storage.py` — `MySQLAccountStore` / `MySQLPanelSettingsStore` / `MySQLGateway`（持久连接 + 自动重连）
- `app_settings.py` — `PanelSettingsStore` 文件后端配置存储
- `persistence.py` — `create_runtime_stores()` 工厂函数，按 `ACCIO_MYSQL` 环境变量决定后端；MySQL 模式下自动从文件补种

**基础设施**
- `config.py` — `Settings` dataclass，从环境变量加载配置，支持 Nuitka 编译路径检测
- `models.py` — `Account` 数据模型与归一化工具函数
- `client.py` — HTTP 客户端封装，支持代理（HTTP/SOCKS）和会话复用
- `model_catalog.py` — 动态模型目录，60 秒缓存
- `usage_stats.py` / `api_logs.py` — 统计与日志

### 数据目录

运行时数据默认位于项目根 `data/`，可通过 `ACCIO_DATA_DIR` 环境变量覆盖：
- `config.json` — 全局配置（管理员密码、会话密钥等）
- `accounts/*.json` — 每个账号一个文件
- `stats.json` — API 调用统计
- `api-logs.jsonl` — API 调用日志

### 关键设计决策

- 所有账号操作通过 `threading.RLock` 保护并发安全
- MySQL 模式使用内存缓存 + write-through 策略减少数据库 I/O
- 后台单调度器按账号下次检查时间巡检额度（非每账号独立定时器）
- API 鉴权统一使用管理员密码，支持 `x-api-key` / `Authorization: Bearer` / Gemini 风格 query 参数

## Git Workflow

本仓库是 `GuJi08233/accio-manager` 的 fork。与上游差异较大，**禁止直接 merge upstream**，只能逐提交 cherry-pick。

```
origin   → caidaoli/accio-manager (push/fetch)
upstream → GuJi08233/accio-manager (fetch only)
```

## Environment Variables

关键环境变量参见 `.env.example`：
- `ACCIO_MYSQL` — MySQL 连接串，设置后启用数据库后端
- `ACCIO_DATA_DIR` — 数据目录路径
- `ACCIO_CALLBACK_PORT` — 服务端口（默认 4097）
- `ACCIO_BASE_URL` — 上游网关地址
