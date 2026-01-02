# Update-Alternatives TUI

一个用于管理 Linux `update-alternatives` 系统的终端用户界面 (TUI) 工具。

## 功能特性

- 📋 **浏览所有 alternatives** - 列表展示系统中所有的 alternatives
- 🔍 **搜索功能** - 快速查找特定的 alternative
- 📊 **详细信息查看** - 查看每个 alternative 的完整信息，包括：
  - 当前选择
  - 所有可用选项及优先级
  - 从属 (slave) 链接
  - 自动/手动模式状态
- ⚙️ **切换 alternative** - 在不同选项之间切换
- 🔄 **设置自动模式** - 将 alternative 设置为自动选择最高优先级
- ➕ **安装新 alternative** - 添加新的 alternative 选项
- ❌ **删除 alternative** - 移除不需要的 alternative 选项

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/update-alternatives-tui.git
cd update-alternatives-tui

# 使用 uv 安装
uv sync

# 运行 (两种命令均可)
uv run update-alternatives-tui
uv run ua-tui  # 简短别名
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `q` | 退出程序 |
| `r` | 刷新列表 |
| `s` | 设置 alternative (手动模式) |
| `a` | 设置为自动模式 |
| `i` | 安装新 alternative |
| `d` | 删除 alternative |
| `/` | 搜索 |
| `?` | 显示帮助 |
| `↑/↓` | 上下移动选择 |
| `Enter` | 确认选择 |
| `Tab` | 切换面板 |
| `Escape` | 清除搜索 / 取消对话框 |
| `g` | 跳转到列表第一项 |
| `G` | 跳转到列表最后一项 |

## 界面说明

### 状态指示器

- **A** (绿色) - 自动模式
- **M** (黄色) - 手动模式
- **●** (绿色) - 当前选择
- **★** (青色) - 最佳选项 (最高优先级)

### 界面布局

```
┌─────────────────────────────────────────────────────────────────┐
│                    Update-Alternatives Manager                   │
├─────────────────────────┬───────────────────────────────────────┤
│    Alternatives         │           Details                      │
│  ┌───────────────────┐  │  ┌─────────────────────────────────┐  │
│  │ A editor          │  │  │ Name: editor                     │  │
│  │ M java            │  │  │ Link: /usr/bin/editor            │  │
│  │ A python          │  │  │ Status: auto                     │  │
│  │ M python3         │  │  │ Current: /usr/bin/vim.basic      │  │
│  │ ...               │  │  │                                   │  │
│  └───────────────────┘  │  │ Alternatives:                     │  │
│                         │  │  ● /usr/bin/vim.basic (50)        │  │
│  [Search...]            │  │    /usr/bin/nano (40)             │  │
│                         │  └─────────────────────────────────┘  │
├─────────────────────────┴───────────────────────────────────────┤
│  [Set] [Auto] [Install] [Delete]                                 │
├─────────────────────────────────────────────────────────────────┤
│  Status: Loaded 42 alternatives                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 权限说明

修改 alternatives 需要 root 权限。程序会自动使用 `sudo` 来执行需要权限的操作。

如果你不想每次都输入密码，可以配置 sudoers 允许无密码执行 `update-alternatives`：

```bash
# 添加到 /etc/sudoers.d/update-alternatives
your_username ALL=(ALL) NOPASSWD: /usr/bin/update-alternatives
```

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/yourusername/update-alternatives-tui.git
cd update-alternatives-tui

# 创建虚拟环境并安装依赖
uv sync

# 运行开发版本
uv run python -m update_alternatives_tui.app
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行所有测试并显示覆盖率
uv run pytest --cov=src/update_alternatives_tui --cov-report=term-missing

# 仅运行单元测试 (跳过集成测试)
uv run pytest -m "not integration"

# 仅运行集成测试 (使用真实系统数据)
uv run pytest -m integration

# 跳过慢速测试
uv run pytest -m "not slow"

# 运行特定模块的测试
uv run pytest tests/test_parser.py -v

# 运行测试并生成 HTML 覆盖率报告
uv run pytest --cov=src/update_alternatives_tui --cov-report=html
```

### 测试分类

- **单元测试**: 测试各个模块的独立功能
- **集成测试** (`@pytest.mark.integration`): 使用真实系统 `update-alternatives` 数据进行测试
- **慢速测试** (`@pytest.mark.slow`): 性能测试等耗时较长的测试

### 项目结构

```
update-alternatives-tui/
├── src/
│   └── update_alternatives_tui/
│       ├── __init__.py      # 包初始化与公共 API 导出
│       ├── app.py           # TUI 应用主程序
│       ├── app_styles.py    # 应用 CSS 样式定义
│       ├── cache.py         # 缓存实现 (TTL 缓存)
│       ├── constants.py     # 常量定义 (颜色、快捷键、配置)
│       ├── exceptions.py    # 自定义异常层次结构
│       ├── executor.py      # 命令执行抽象层 (支持重试、超时)
│       ├── logging.py       # 日志配置
│       ├── models.py        # 数据模型 (Alternative, AlternativeGroup 等)
│       ├── parser.py        # update-alternatives 输出解析器
│       ├── service.py       # 业务逻辑服务层
│       ├── types.py         # 类型定义与协议
│       ├── utils.py         # 工具函数 (转义、截断等)
│       ├── widgets/         # UI 组件包
│       │   ├── __init__.py  # 组件导出
│       │   ├── base.py      # 基础组件 (StatusWidget, DetailPanel)
│       │   ├── dialogs.py   # 对话框组件
│       │   ├── messages.py  # 消息定义
│       │   └── styles.py    # 组件 CSS 样式
│       └── py.typed         # PEP 561 类型标记
├── tests/                   # 测试文件
│   ├── conftest.py          # pytest 配置与 fixtures
│   └── test_*.py            # 各模块测试
├── pyproject.toml           # 项目配置 (uv/hatch)
├── README.md                # 项目说明
├── LICENSE                  # MIT 许可证
└── uv.lock                  # 依赖锁定文件
```

## 架构设计

项目采用分层架构：

```
┌─────────────────────────────────────────────┐
│              app.py (TUI 界面)               │
├─────────────────────────────────────────────┤
│          widgets/ (UI 组件包)                │
│   base.py | dialogs.py | messages.py        │
├─────────────────────────────────────────────┤
│         service.py (业务逻辑)                │
│            cache.py (缓存)                   │
├─────────────────────────────────────────────┤
│  parser.py (解析)  │  executor.py (执行)     │
├─────────────────────────────────────────────┤
│    models.py (数据模型)  │  types.py (类型)   │
└─────────────────────────────────────────────┘
```

## 相关资源

- [update-alternatives 手册](https://manpages.debian.org/update-alternatives)
- [Textual 文档](https://textual.textualize.io/)
