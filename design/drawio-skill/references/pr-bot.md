# PR 图表差异报告

对当前 PR 涉及的 `.drawio` 文件生成基线图、候选图、着色差异图和 Markdown。由目标仓库的 CI 发布生成的报告和图片制品。

## 在本地生成

先按 PR 实际目标仓库和分支获取基线与候选提交，确保两个引用在被检出的仓库中可用。从 CCS 根目录执行：

```bash
python design/drawio-skill/scripts/prdiff.py --repo <项目检出目录> \
  --base <base-sha> --head <head-sha> --out-dir drawio-pr -o drawio-pr/report.md
```

脚本在 PATH 中查找 `drawio` 或 `draw.io`。Windows 已安装桌面版时，可直接传入安装路径。PowerShell 示例：

```powershell
python design/drawio-skill/scripts/prdiff.py --repo '<项目检出目录>' --base '<base-sha>' --head '<head-sha>' --drawio 'D:\Program Files\draw.io\draw.io.exe' --out-dir drawio-pr -o drawio-pr/report.md
```

脚本通过 draw.io CLI 导出 PNG。着色差异图需要 Graphviz 的 `dot` 在 PATH 中。修改的图通过同目录 `drawiodiff.py` 和 `autolayout.py` 生成差异图。无头 Linux runner 使用虚拟显示（如 `xvfb-run`）。图片导出不完整时，结合报告和运行日志确认覆盖范围，文件清单仍可用于评审。

## 接入目标仓库的 CI

1. 在现有流水线中检出可解析的 PR base 和 head，并调用上述脚本。
2. 上传完整 `drawio-pr/`，包含 Markdown 与相对路径指向的图片。需要展示摘要时链接流水线制品。
3. 项目已授权更新 PR 评论时，复用其评论发布能力，用稳定标记定位现有报告并确认仓库、PR、提交和制品链接。评论中的图使用评审者可以访问的地址。先验证制品读回，再记录视觉验收结果。

CCS 提供报告脚本。工作流、评论和制品上传由目标仓库接入。PR 操作见 [PR 验证记录与评审线程](../../../independent-tools/branch-manager/references/pr-records.md)。
