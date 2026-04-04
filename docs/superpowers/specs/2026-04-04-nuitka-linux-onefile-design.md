# Accio Nuitka Linux 单文件发布设计

**日期：** 2026-04-04

## 目标

在 GitHub Actions 中使用 Nuitka 为 Accio 生成可在 Linux `amd64` 上运行的单文件产物，并仅在推送 `vX.Y.Z` tag 时触发构建。

## 当前问题

- 仓库没有 GitHub Actions 工作流，无法自动构建单文件发布产物。
- 模板文件位于 `accio_panel/templates/`，如果 Nuitka 未显式包含运行时数据，面板页面会直接失效。
- 默认数据目录依赖源码路径推导；在 Nuitka `--onefile` 模式下，源码路径指向临时解包目录，不适合作为持久化数据目录。
- 版本号当前只存在于 `pyproject.toml`，tag 和项目版本之间没有校验，容易出现 `vX.Y.Z` 与项目版本不一致的脏发布。

## 设计

### 1. 触发方式

- 新增 GitHub Actions workflow，仅匹配 `v*.*.*` tag。
- workflow 在构建前校验 `github.ref_name` 与 `pyproject.toml` 中的 `project.version` 是否完全一致，不一致直接失败。

### 2. 构建方式

- 使用 `Nuitka/Nuitka-Action` 构建 `main.py`。
- 目标平台固定为 GitHub Ubuntu runner 上的 `x64` Python 3.12。
- 产物模式使用 `onefile`。
- 显式包含 `accio_panel` 的包数据，使模板目录进入单文件产物。

### 3. 运行时路径修正

- 保持 `ACCIO_DATA_DIR` 为最高优先级。
- 源码运行时默认数据目录继续使用仓库根目录下的 `data/`。
- Nuitka 编译后的运行时默认数据目录改为“可执行文件同级目录下的 `data/`”。
- 模板目录继续按包内相对路径读取，因为它属于打包进入 onefile 的内部数据。

### 4. 文档

- README 增加 tag 发布说明，明确只接受 `vX.Y.Z`，例如 `v0.1.0`。
- README 说明产物名称和下载位置为 Actions artifact。

## 验证

- 单元测试覆盖：
  - Nuitka onefile 运行时默认数据目录解析。
  - `ACCIO_DATA_DIR` 覆盖默认路径。
  - tag 与项目版本校验逻辑。
- 本地验证：
  - 运行完整测试集。
  - 运行一次本地 Nuitka onefile 构建命令，验证编译链路与数据文件包含参数可用。
