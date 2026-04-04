# Accio Nuitka Linux 单文件发布 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Accio 增加基于 `vX.Y.Z` tag 触发的 GitHub Actions Nuitka Linux `amd64` 单文件构建流程，并修正 onefile 下的数据目录默认值。

**Architecture:** 把易出错的发布规则拆成两个明确边界：一是 Python 侧的运行时路径解析，二是 CI 侧的 tag/version 校验与构建编排。模板仍然作为包数据进入 onefile 内部，持久化数据则固定落在可执行文件同级目录，避免写入临时解包目录。

**Tech Stack:** Python 3.12, unittest, GitHub Actions, Nuitka, Nuitka/Nuitka-Action

---

### Task 1: 先把 onefile 路径和 tag 校验写成失败测试

**Files:**
- Modify: `tests/test_runtime_storage.py`
- Create: `tests/test_release_build.py`

- [ ] **Step 1: 为 onefile 默认数据目录写测试**

```python
with patch.object(config_module, "__compiled__", compiled, create=True):
    settings = config_module.Settings()
assert settings.data_dir == Path("/tmp/app") / "data"
```

- [ ] **Step 2: 跑测试确认当前失败**

Run: `uv run python -m unittest tests.test_runtime_storage tests.test_release_build -v`
Expected: FAIL，因为当前实现仍然把默认数据目录绑在源码路径，且还没有 tag 校验脚本。

- [ ] **Step 3: 为 tag/version 校验写测试**

```python
self.assertEqual(validate_release_tag("v0.1.0", "0.1.0"), "v0.1.0")
with self.assertRaises(ValueError):
    validate_release_tag("v0.1", "0.1.0")
```

- [ ] **Step 4: 再次跑测试确认失败原因正确**

Run: `uv run python -m unittest tests.test_runtime_storage tests.test_release_build -v`
Expected: FAIL，错误集中在缺少校验脚本或路径行为不匹配。

### Task 2: 实现最小必要的发布辅助代码

**Files:**
- Modify: `accio_panel/config.py`
- Create: `scripts/validate_release_tag.py`

- [ ] **Step 1: 抽出运行时根目录解析**

```python
def _runtime_root() -> Path:
    ...
```

- [ ] **Step 2: 让默认数据目录在 compiled 与 source 两种模式下返回稳定路径**

```python
def _default_data_dir() -> Path:
    return Path(os.getenv("ACCIO_DATA_DIR", str(_runtime_root() / "data")))
```

- [ ] **Step 3: 添加 tag/version 校验脚本**

```python
def validate_release_tag(tag_name: str, version: str) -> str:
    ...
```

- [ ] **Step 4: 跑测试确认转绿**

Run: `uv run python -m unittest tests.test_runtime_storage tests.test_release_build -v`
Expected: PASS

### Task 3: 增加 GitHub Actions Nuitka 工作流和文档

**Files:**
- Create: `.github/workflows/build-linux-onefile.yml`
- Modify: `README.md`

- [ ] **Step 1: 新增 tag 触发 workflow**

```yaml
on:
  push:
    tags:
      - "v*.*.*"
```

- [ ] **Step 2: 用 Nuitka Action 构建 Linux x64 onefile，并包含包数据**

```yaml
- uses: Nuitka/Nuitka-Action@v1.3
  with:
    nuitka-version: 4.0
    script-name: main.py
    mode: onefile
    include-package-data: accio_panel
```

- [ ] **Step 3: 上传产物并在 README 记录发布方式**

```md
git tag v0.1.0
git push origin v0.1.0
```

- [ ] **Step 4: 运行完整验证**

Run: `uv run python -m unittest -v`
Expected: PASS

- [ ] **Step 5: 运行本地 Nuitka 构建验证**

Run: `uv run --with "nuitka[onefile]==4.0" python -m nuitka --onefile --include-package-data=accio_panel main.py`
Expected: exit 0，并在项目根目录附近生成单文件产物。
