# Playwright 测试依赖安装指南

---

## 一、Python Playwright 包安装

```bash
# 添加到项目 dev 依赖
uv add --dev playwright

# 单独安装（非 uv 项目）
pip install playwright
```

---

## 二、浏览器安装

### 标准安装（仅 Chromium，约 183MB）

```bash
# uv 项目
uv run playwright install chromium

# pip 项目
python -m playwright install chromium
```

### 国内镜像加速

**方法1：环境变量**（推荐）
```bash
# Windows PowerShell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/"
uv run playwright install chromium

# Linux / macOS / Git Bash
export PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/"
uv run playwright install chromium
```

**方法2：配置文件**（持久生效）

在项目根目录或用户目录创建/编辑 `.npmrc`：
```
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
```

### 安装所有浏览器（约 500MB+）

```bash
# 如不需要全部浏览器，仅装 chromium 即可
uv run playwright install            # 安装 chromium + firefox + webkit
```

---

## 三、Playwright MCP 浏览器安装

当 opencode 配置了 `@playwright/mcp` 时，MCP 使用独立版本的 Playwright Core，需要单独安装浏览器：

```bash
# 方法1: 用 MCP 自带工具安装
npx @playwright/mcp install-browser chrome-for-testing

# 方法2: 指定已有浏览器路径（避开下载）
# 在 opencode.jsonc 的 command 中添加:
# "--executable-path", "C:\\Users\\<user>\\AppData\\Local\\ms-playwright\\chromium-<ver>\\chrome-win64\\chrome.exe"
```

> **注意**：Python `playwright` 和 npm `@playwright/mcp` 的 playwright-core 版本可能不同，浏览器版本号也会不同。建议分别安装。

---

## 四、常见问题

### ECONNRESET / 下载中断

国内访问官方 CDN 可能丢包。解决方案：

1. **使用镜像**（见上方）
2. **手动下载**：
   - 从 https://cdn.playwright.dev/builds/cft/ 找到对应版本的 `win64/chrome-win64.zip`
   - 使用支持断点续传的工具（如 `aria2c`）下载
   - 解压到 `%LOCALAPPDATA%/ms-playwright/` 对应目录

### 网络代理

```bash
# 如使用代理
set HTTP_PROXY=http://127.0.0.1:7890
set HTTPS_PROXY=http://127.0.0.1:7890
```

### 硬盘空间

Playwright Chromium 下载约 183MB，解压后约 350MB。确保 `%LOCALAPPDATA%/ms-playwright/` 所在盘有足够空间。

---

## 五、验证安装

```bash
# Python Playwright
uv run python -c "from playwright.sync_api import sync_playwright; print('OK')"

# 列出已安装浏览器
uv run playwright install --dry-run

# npm MCP
npx @playwright/mcp --help
```
