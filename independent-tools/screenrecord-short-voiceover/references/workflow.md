# 本地制作脚本

依赖 Python 3.10+、`imageio-ffmpeg`、`pillow`、`edge-tts`。可用现有 FFmpeg（环境变量 `FFMPEG`）或 imageio-ffmpeg 自带版本。Windows 路径有空格时加引号。下面的路径均为使用者自行选择，不包含作者机器路径。

```powershell
python -m venv .video-tools
.\.video-tools\Scripts\python -m pip install imageio-ffmpeg pillow edge-tts
.\.video-tools\Scripts\python <skill目录>/scripts/video_workflow.py inspect input.mp4 --out inspection --step 5
.\.video-tools\Scripts\python <skill目录>/scripts/video_workflow.py render plan.json
.\.video-tools\Scripts\python <skill目录>/scripts/video_workflow.py verify output/demo.mp4 --limit-seconds 60
```

`inspect` 输出媒体信息与每页 12 张的带时间标签联系表。人工查看缩略图并在关键点精查，不能直接拿粗采样当逐帧证据。`--step` 单位秒。

## plan.json

每条视频一个计划。所有相对路径都相对于计划文件目录，源文件不得与输出相同。可先用短片段试做声音。

```json
{
  "source": "input.mp4",
  "output": "output/demo.mp4",
  "limit_seconds": 60,
  "voice": "zh-CN-YunxiNeural",
  "rate": "+0%",
  "max_voice_speed": 1.3,
  "segments": [
    {"start": 0, "end": 12, "duration": 8, "label": "输入并启动"},
    {"start": 12, "end": 72, "duration": 3, "label": "等待生成"},
    {"start": 72, "end": 82, "duration": 10, "label": "核对结果"}
  ],
  "narration": [
    {"start": 0.5, "end": 7.8, "text": "输入需求并启动生成。"},
    {"start": 11.2, "end": 20.5, "text": "查看生成的 Python 脚本。", "spoken_text": "查看生成的派森脚本。"}
  ]
}
```

`segments` 要按源时间连续且从 0 开始到原片结束；示例假设原片 82 秒。只有用户允许删减时设置 `allow_cuts: true`，仍要求片段有序且不重叠。

`narration` 的 start/end 是成片秒数。可以用 `audio_file` 替代 TTS，但须核对来源、声音一致性与隐私。`text` 保留正式文稿，`spoken_text` 仅控制合成；更改任一合成参数都会更新语音缓存。语音槽不能重叠，超时内容以变速适配但不能超过 `max_voice_speed`，不允许偷偷截断。

默认以第一份素材的分辨率为画布，奇数宽高向下取偶数；也可显式指定 `canvas`。所有片段保持比例缩放并留黑边，不拉伸，输出 H.264、30fps、AAC；原始声音不保留，只使用计划中的配音。工作缓存位于输出目录下 `.video-work/<计划名称>/`，不是交付文件。输入视频、录音与计划不要放在该缓存目录内。每个并行任务用独立计划名称和输出路径，避免覆盖。

源视频内容哈希、裁剪/高亮、画布、编码参数与脚本版本参与画面缓存；替换同路径原片也会失效。字幕单独缓存合成画面，只改声音无需重编画面。更换编码策略时同步提升代码中的 CACHE_VERSION。每次计算源文件哈希会完整读一遍素材。

渲染后生成 `<视频名>.timing.json`，记录素材标识、源时间、成片时间、倍速、正式稿、合成稿、字幕和语音速度，便于后续按秒修订。另导出 `<视频名>.srt`；无字幕时为空文件，避免上次字幕被误用。时间线按 30fps 对齐，锚点可能有一帧以内取整；总时长仍须严格小于上限。只有通过尺寸、完整解码和音频能量检查后才替换最终视频。脚本检查不保证发音、音色或业务语义正确，必须人工/代理试听与观察。

网络 TTS 每段最多尝试三次，每次 35 秒；失败后保留已完成缓存并报错，不静默换声音。TTS 依赖服务可用性，不保证离线可用。音频采用有限 PCM 缓冲，不使用无限补静音管线。

## 产品介绍片：多素材、字幕与重点标注

先按 [产品介绍片策划指南](product-intro.md) 做卖点与镜头映射，再填写计划。`source`（旧格式）与 `sources`（多素材）只能二选一；多素材的每个片段显式填写素材 ID。片段数组顺序就是成片顺序。

```json
{
  "sources": {"operation": "operation.mp4", "knowledge": "knowledge-raw.mp4"},
  "output": "output/product-intro.mp4",
  "limit_seconds": 21,
  "allow_cuts": true,
  "canvas": {"width": 1280, "height": 720},
  "highlight_color": "#FFD166",
  "subtitles": true,
  "subtitle_font": "Microsoft YaHei",
  "subtitle_size": 30,
  "segments": [
    {"source": "operation", "start": 12, "end": 20, "duration": 6,
     "label": "关键操作", "crop": [200, 160, 1200, 720], "highlight": [400, 300, 300, 120]},
    {"source": "knowledge", "start": 40, "end": 52, "duration": 8, "label": "知识查询"},
    {"source": "operation", "start": 80, "end": 88, "duration": 6, "label": "结果与下一步"}
  ],
  "narration": [
    {"start": 0.5, "end": 5.8, "text": "用真实操作展示一个核心功能。", "audio_file": "voice-1.wav"},
    {"start": 6.5, "end": 13.8, "text": "展示查询结果，并核对依据。", "audio_file": "voice-2.wav"},
    {"start": 14.5, "end": 19.8, "text": "了解产品，预约演示。", "audio_file": "voice-3.wav"}
  ]
}
```

这是格式示例，原始素材须足够长，裁剪示例假设操作画面至少 1400×880；文字仅作占位，必须换成素材可证实的表述。配音文件替换为真实录音，或去掉 `audio_file` 使用同一音色 TTS。

| 字段 | 含义和边界 |
|---|---|
| `sources` | 素材 ID → 路径，路径相对计划文件；覆盖检查包括所有输入视频及外部配音 |
| `allow_cuts` | 默认 false，每个已声明素材都须完整覆盖；true 允许选段和省略未使用素材 |
| `allow_reorder` | 默认 false，同一素材须保持顺序且不重叠；true 允许倒序或复用镜头，须同时允许 cuts，不可用来伪造操作因果 |
| `canvas` | 偶数宽高；所有素材统一尺寸、30fps 与像素宽高比，保持比例并补黑边 |
| `crop` | `[x,y,width,height]`，坐标基于原始显示画面（旋转后、缩放前），四个值须为偶数且位于素材内；静态裁剪，不是动态镜头 |
| `highlight` | 同一原始画面坐标系的矩形，须完全落在 crop 内；整段显示高亮边框，需要更短高亮时拆段 |
| `label` | 仅用于时间记录，不会自动出现在画面上 |
| `subtitles` | 默认 false；true 按 narration 正式 `text` 生成字幕，不使用 `spoken_text`，外部录音也须提供正式稿 |
| `captions` | 可选的 `{start,end,text}` 数组，设置后替代自动字幕；成片时间，须有序、不重叠且不超界；空数组明确关闭字幕 |
| `subtitle_font` / `subtitle_size` | 本机已安装字体与画布像素字号；Windows 默认微软雅黑，其他平台默认 sans-serif，中文字体是否可用仍须看图 |

字幕为烧录字幕，同时导出 SRT；按画布留边、白字黑描边，最多两行，过长会报错，要求拆分字幕槽或缩短文稿，绝不截字。字幕不会自动避让界面按钮；关键区域在下方时调整构图或字幕时间。烧录需要 FFmpeg 带 `ass`/libass 滤镜；缺失时更换具备该能力的本地 FFmpeg，不能声称成功。

脚本不支持自动补录产品、动态跟踪、复杂品牌动画或配乐混音。竖屏可设置竖画布并逐镜选择 crop，但缩放留黑边不等于完成适合竖屏的视觉设计。

## 验证脚本升级

计划校验不需要网络；真实渲染测试还需 imageio-ffmpeg（或设置 `FFMPEG`）与 libass。测试用本地合成音频，不依赖在线 TTS。

```powershell
python -m unittest discover -s <skill目录>/tests -p "test_*.py"
$env:VIDEO_WORKFLOW_SMOKE = "1"
python -m unittest discover -s <skill目录>/tests -p "test_*.py"
```

第一条默认跳过真实渲染，第二条覆盖异尺寸拼接、字幕、高亮/裁剪、只改声音的缓存复用、原片替换及旧计划。技术测试与策划 eval 均不能替代成片试听和真实观众理解度验证。

## 成片诊断 audit

`audit` 只读视频，把UTF-8 编码的结构化诊断 JSON 输出到终端；不会重剪、自动删静音或覆盖素材。使用诊断结果回看相应时间点，再作编辑决定：

```powershell
python <skill目录>/scripts/video_workflow.py audit output/product-intro.mp4 --plan plan.json
python <skill目录>/scripts/video_workflow.py audit output/product-intro.mp4 --silence-seconds 2
# 仅在用户明确要求静音版本时使用；render 仍是配音制作流程。
python <skill目录>/scripts/video_workflow.py audit output/silent-loop.mp4 --allow-silent
```

- 完整解码与音量检查后，定位低于 −40 dB 且连续至少 1.5 秒的静音区间（包括片尾）；可用 `--silence-seconds` 调整时间阈值。未声明允许静音时，缺失音轨或全静音仍会报错。
- 提供 `--plan` 后，核对其 output、总时长、尺寸与当前视频，再列出小于 1 倍的慢放、估算留边面积至少 25%、高亮宽度占有效源画面至少 80% 的片段。提示包含成片起止时间和原因。
- 留边和高亮是**计划估算**，不是像素级检测；也不识别源片自带黑边。路径/时长/尺寸一致不能证明计划与成片内容一致，须看图确认。未提供计划时这三项未检查，报告会明确说明。
- `technical_status=PASS` 表示所列技术检查通过；接近满幅的音轨为 `WARN`。`editorial_status` 始终是 `PENDING`，即便没有告警也不代表内容、构图、字幕、试听或营销效果已通过。退出码 0 只表示诊断成功。
- 阈值是审看提示，不是自动否决规则。阅读结果、静音循环片、完整竖素材及整行表格框都可能合理；依据观看任务保留或修改，并在交付说明中记录理由。没有听音工具时不得借诊断结果宣称已试听。
