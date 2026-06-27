# PBI-BgDesign 设计文档

## 项目概述

PBI-BgDesign 是一个桌面工具，用于为 Power BI 报表设计美观的背景图。它读取 .pbix 文件中的报表布局，分析视觉对象的位置和类型，然后由 AI（Claude）根据布局结构设计背景和装饰元素。用户预览效果、确认导出后，将 PNG/SVG 图片用作 Power BI 报表页背景。

## 核心工作流

```
1. 用户在 Power BI 中调整报表布局（图表位置、大小）
2. 将 .pbix 文件加载到 PBI-BgDesign
3. 工具解析布局 → 输出结构化数据（视觉对象位置、类型、尺寸）
4. 用户选择布局模式（固定/弹性/自由），调用 AI 设计
5. AI 根据布局结构和约束生成背景+装饰设计方案（SVG）
6. 工具渲染预览（AI 设计 + 模拟图表叠加）
7. 用户勾选/编辑元素，反馈调整
8. 满意后导出 PNG/SVG → 回到 Power BI 设为页面背景
```

## 技术栈

- Python 3.11+
- PyQt6（桌面 GUI + 图形渲染）
- anthropic（Claude API SDK，支持流式输出和工具调用）
- mcp（Python MCP SDK，作为 MCP 客户端连接外部服务）
- 内置 SVG 生成和渲染

## 模块架构

```
┌─────────────────────────────────────────────────────────┐
│                    PBI-BgDesign 桌面应用                   │
├─────────────┬─────────────────────────┬─────────────────┤
│             │                         │                 │
│  PBIX 解析层  │     渲染 & 交互层         │    导出层        │
│             │                         │                 │
│ • ZIP 解包   │ • QGraphicsScene 画布    │ • PNG 导出      │
│ • Layout    │ • 视觉对象图形化          │   (QPainter →   │
│   JSON 解析  │ • 重叠检测与分组          │    QImage)      │
│ • 资源提取   │ • 勾选/编辑交互          │ • SVG 导出      │
│   (PNG/SVG) │ • 全屏预览              │   (QSvgGen)    │
│             │                         │                 │
└─────────────┴─────────────────────────┴─────────────────┘
```

### 模块文件

| 模块 | 文件 | 职责 |
|------|------|------|
| pbix_parser | pbix_parser.py | 解压 .pbix，解析 Layout JSON，提取页面/对象/资源 |
| layout_analyzer | layout_analyzer.py | 分析视觉对象重叠关系，自动分组，生成布局摘要 |
| ai_designer | ai_designer.py | 调用 Claude API（流式+工具调用），MCP 客户端，Skill 加载器，管理对话上下文 |
| mock_renderer | mock_renderer.py | 为动态图表生成模拟图（环形图、折线图等示意图） |
| svg_design | svg_design.py | 解析 AI 生成的 SVG，转换为 QGraphicsItem |
| renderer | renderer.py | 将所有层（AI设计+模拟图表+文本）渲染到 QGraphicsScene |
| exporter | exporter.py | 将筛选后的场景导出为 PNG / SVG |
| main_window | main_window.py | 主界面：页面列表、画布预览、对象列表、对话面板、工具栏 |
| fullscreen | fullscreen.py | 全屏预览窗口 |
| app | app.py | 应用入口，处理命令行参数（Power BI 外部工具传入 .pbix 路径） |

### 数据流

```
.pbix 文件
    ↓ [pbix_parser]
PbixData（页面列表、视觉对象、资源文件）
    ↓ [layout_analyzer]
LayoutAnalysis（重叠分组、布局摘要、元素分类）
    ↓
用户选择布局模式
    ↓ [ai_designer → Claude API]
AIDesign（装饰元素 SVG）←→ 用户对话反馈迭代
    ↓ [svg_design]
QGraphicsItem 列表
    ↓ [mock_renderer]
MockCharts（模拟图表图形）
    ↓ [renderer]
QGraphicsScene（多层合成预览）
    ↓ [用户勾选/编辑]
    ↓ [exporter]
PNG / SVG 背景图
```

## PBIX 解析器（pbix_parser.py）

### .pbix 文件结构

.pbix 本质是 ZIP 文件，关键内容：

| 路径 | 说明 |
|------|------|
| `Report/Layout` | UTF-16-LE 编码的 JSON，包含所有页面和视觉对象定义 |
| `Report/StaticResources/RegisteredResources/` | 静态资源（PNG、SVG 图片） |
| `Report/CustomVisuals/` | 自定义视觉对象定义 |

### Layout JSON 结构

```json
{
  "sections": [
    {
      "name": "页面ID",
      "displayName": "页面名称",
      "width": 1280,
      "height": 720,
      "displayOption": 1,
      "visualContainers": [
        {
          "x": 100.0,
          "y": 50.0,
          "z": 1000,
          "width": 300.0,
          "height": 200.0,
          "config": "{\"singleVisual\":{\"visualType\":\"donutChart\",\"objects\":{...}}}"
        }
      ]
    }
  ]
}
```

注意：
- Layout 文件为 UTF-16-LE 编码，需要 `decode('utf-16-le')` 处理
- `config` 字段是嵌套的 JSON 字符串，需要二次解析
- 图表标题存储在 config 的 `objects.title` 或类似字段中

### 输出数据结构

```python
@dataclass
class VisualObject:
    id: str                    # 唯一标识
    visual_type: str           # "shape" | "image" | "textbox" | "donutChart" | ...
    x: float                   # 位置 x
    y: float                   # 位置 y
    z: int                     # 层级
    width: float               # 宽度
    height: float              # 高度
    title: str | None          # 图表标题（如果有）
    config: dict               # 原始 config 解析结果
    resource_path: str | None  # 关联的图片资源路径（如果是 image 类型）

@dataclass
class OverlapGroup:
    id: str                    # 组 ID
    visuals: list[VisualObject]  # 组内所有视觉对象
    bbox: tuple                # 组的整体边界框 (x, y, w, h)

@dataclass
class PageData:
    name: str
    display_name: str
    width: float
    height: float
    visuals: list[VisualObject]

@dataclass
class PbixData:
    pages: list[PageData]
    resources: dict[str, bytes]   # {文件名: 二进制内容}
    theme: dict | None
```

## 布局分析器（layout_analyzer.py）

### 重叠检测

通过计算每对视觉对象的边界框重叠面积来检测重叠：

- 两个对象的重叠面积占较小对象面积 > 50% → 归为同一重叠组
- 使用 z-order 确定组内层级关系
- 支持传递性：A 与 B 重叠，B 与 C 重叠 → A、B、C 同组

### 元素分类

每个视觉对象归入以下类别之一：

| 类别 | 标签 | 可勾选 | 可编辑 | 说明 |
|------|------|--------|--------|------|
| AI 设计元素 | [AI设计] | ✅ | ❌ | AI 生成的背景、装饰形状、色块等 |
| 独立文本框 | [文本] | ✅ | ✅ | 原 .pbix 中的 textbox |
| 图表标题 | [标题] | ✅ | ✅ | 从动态图表 config 中提取的标题 |
| 动态图表 | [图表] | ❌ | ❌ | 仅预览参考，永不导出 |

### 布局摘要（供 AI 使用）

生成一份结构化的布局描述，包含：
- 画布尺寸
- 每个视觉对象的类型、位置、尺寸
- 重叠分组信息
- 视觉对象之间的间距关系
- 图表标题内容

## 布局模式

用户在设计前选择布局模式，决定 AI 的约束程度：

| 模式 | 名称 | AI 约束 |
|------|------|---------|
| 模式 1 | 固定布局 | 所有视觉对象位置和尺寸锁定，AI 只在空隙和周边设计装饰元素 |
| 模式 2 | 弹性布局 | AI 可微调间距（≤30%）和尺寸（≤20%），但不改变相对位置关系 |
| 模式 3 | 自由设计 | AI 可根据图表类型和数量重新规划布局 |

## AI 设计引擎（ai_designer.py）

### 技术实现

使用 `anthropic` Python SDK 直接调用 Claude API，不依赖 Claude Code。支持流式输出、工具调用、MCP 客户端和 Skill 加载。

### 四大能力

#### 1. 流式输出（Streaming）

- 使用 `client.messages.create(stream=True)` 流式接收响应
- 对话面板实时逐字显示 AI 的设计说明和思考过程
- SVG 代码在代码块中逐行输出，工具检测到完整 `<svg>...</svg>` 后自动解析渲染
- 用户无需等待完整响应即可看到设计进展

#### 2. 工具调用（Tool Use）

AI 在设计过程中可以调用内置工具获取信息或执行操作：

**查询类工具：**

| 工具名 | 参数 | 作用 |
|--------|------|------|
| `get_layout_info` | page_name | 获取指定页面的完整布局数据 |
| `get_visual_details` | visual_id | 获取某个视觉对象的完整 config（标题、样式、数据字段等） |
| `get_overlap_groups` | page_name | 获取重叠分组的详细信息 |
| `get_spacing_info` | page_name | 获取视觉对象之间的间距关系 |
| `list_resources` | - | 列出 .pbix 中可用的图片资源 |

**操作类工具：**

| 工具名 | 参数 | 作用 |
|--------|------|------|
| `apply_design` | svg_code | 将 SVG 设计应用到预览画布 |
| `add_text_element` | text, x, y, font_size, color | 在指定位置添加文本元素 |
| `highlight_visual` | visual_id, color | 在预览中高亮某个视觉对象（辅助说明） |
| `load_skill` | skill_name | 加载指定 Skill 的完整内容到对话上下文 |
| `list_skills` | - | 列出所有可用的 Skill（name + description） |

AI 可以主动调用这些工具，比如：
- "我需要先看看这个页面有哪些视觉对象" → 调用 `get_layout_info`
- "让我看看这个图表的标题是什么" → 调用 `get_visual_details`
- "设计完成，让我应用到预览" → 调用 `apply_design`

#### 3. MCP 客户端（连接外部服务）

使用 Python `mcp` SDK 作为 MCP 客户端，连接用户配置的外部 MCP Server：

**支持的 MCP 服务示例：**

| MCP 服务 | 用途 |
|----------|------|
| WebSearch | AI 搜索设计灵感、配色方案、行业报告风格 |
| 图片处理 | 处理用户提供的 Logo、素材图片 |
| 图标库 | 搜索和获取图标 SVG |
| 自定义 MCP | 用户自行开发的其他服务 |

**MCP 工具注册流程：**
1. 启动时根据设置面板的配置连接各 MCP Server
2. 获取每个 MCP Server 提供的工具列表
3. 将 MCP 工具与内置工具合并，一起注册到 Claude API 的 `tools` 参数中
4. AI 可以在设计过程中调用任何已注册的工具（内置或 MCP）

#### 4. Skill 加载器（按需加载，对齐 Claude Code 模式）

从指定目录加载 Skill 文件（兼容 Claude Code Skill 格式），AI 通过 `load_skill` 工具按需加载 Skill 内容。

**Skill 文件目录：** `~/.pbi_bgdesign/skills/`

**Skill 文件格式：**

```markdown
---
name: frontend-designer
description: Expert frontend designer with strong visual taste
whenToUse: When designing visual layouts, color schemes, or UI elements
---

# Frontend Designer

You are an expert frontend designer...
（具体的设计指导内容）
```

**触发机制（对齐 Claude Code）：**

1. 启动时扫描 skills 目录，仅解析 frontmatter（`name`、`description`、`whenToUse`）
2. 将所有 Skill 的**摘要**（不含完整内容）注入 system prompt，告知 AI 有哪些 Skill 可用
3. AI 根据上下文判断需要使用某个 Skill → 调用 `load_skill(skill_name)` 工具
4. 工具返回该 Skill 的完整内容，注入到对话上下文中生效
5. 用户也可以在对话中手动指定，如 "使用 frontend-designer skill 来设计"
6. Skill 文件变更时自动热加载摘要

**system prompt 中的 Skill 摘要示例：**

```
Available skills:
- frontend-designer: Expert frontend designer with strong visual taste
  TRIGGER — use when designing visual layouts, color schemes, or UI elements
- data-viz-expert: Data visualization specialist
  TRIGGER — use when designing chart-heavy pages or data dashboards

Use the load_skill tool to load a skill's full instructions when needed.
```

**Skill 与 MCP 的关系：**

| 能力 | 作用 | 触发方式 |
|------|------|---------|
| Skill | 指导 AI「怎么设计」（风格、原则、约束） | AI 调用 `load_skill` 工具按需加载，或用户手动指定 |
| MCP | 给 AI「额外能力」（搜索、图片处理等） | AI 通过工具调用主动使用 |
| 内置工具 | 让 AI「了解布局」（查询页面、对象信息） | AI 通过工具调用主动使用 |

### 调用流程

```
用户点击「AI 设计」
    ↓
构建 system prompt（含 Skill 摘要）+ 布局摘要
    ↓
调用 Claude API（stream=True, tools=[内置工具 + MCP工具]）
    ↓
流式接收响应：
    ├── 文本内容 → 实时显示在对话面板
    ├── tool_use 请求 → 执行工具，返回结果给 API
    │     ├── 内置工具 → 本地执行（查询布局、应用设计、加载 Skill 等）
    │     └── MCP 工具 → 通过 MCP 客户端转发到外部 Server
    └── SVG 代码块 → 检测完整性后自动渲染到画布
    ↓
设计完成，用户预览
    ↓
用户在对话面板输入反馈 → 新一轮 API 调用（保留上下文）
```

### 对话面板

工具界面右侧包含对话面板（可折叠）：
- 实时流式显示 AI 的设计说明和工具调用过程
- 用户可输入文字反馈（如"把分隔条颜色换成深灰色"）
- 每次迭代保留完整上下文，AI 基于当前设计修改
- 显示工具调用状态（如 "正在查询布局信息..." "正在搜索设计灵感..."）

### API 配置（设置面板）

| 配置项 | 说明 |
|--------|------|
| API Key | Anthropic API Key，加密存储在本地 `~/.pbi_bgdesign/config.json` |
| 模型选择 | 默认 claude-sonnet-4-6，可选 opus/haiku |
| MCP 服务列表 | 配置 MCP Server 地址和类型，支持添加/删除/启用/禁用 |
| Skills 目录 | 显示当前 Skills 目录路径，已加载的 Skill 列表，提供「打开目录」按钮 |
| Token 用量 | 显示本次会话和累计 token 消耗，可设置单次设计上限 |

### MCP 配置格式

存储在 `~/.pbi_bgdesign/mcp_config.json`，采用字典格式（与 Claude Code 一致）：
```json
{
  "mcpServers": {
    "web-search": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-web-search"]
    },
    "image-proc": {
      "url": "http://localhost:3001/sse"
    }
  }
}
```

传输类型自动推断：有 `command` 字段为 stdio，有 `url` 字段为 sse。

### Prompt 结构

发送给 Claude 的 system prompt：

```
你是一个 Power BI 报表背景设计师。你的任务是根据报表布局信息设计美观的背景和装饰元素。

## 工作流程

**在开始设计之前，你必须先了解用户的偏好。请按以下步骤引导：**

1. 先简要分析布局结构（有多少图表、什么类型、页面用途）
2. 主动询问用户偏好（每次 1-2 个问题，不要一次问太多）：
   - 整体风格倾向（商务简约 / 科技感 / 清新活泼 / 深色系 / 明亮系）
   - 主色调偏好（冷色调 / 暖色调 / 特定颜色）
   - 装饰元素密度（简洁留白多 / 丰富填充多）
   - 是否有企业品牌色需要遵循
3. 根据回答提出 1-2 个设计方向建议，等用户确认
4. 确认后再开始生成设计

如果用户上传了参考图片，先分析图片的风格特征（配色、布局、装饰元素、整体氛围），提取关键风格要素作为设计依据。

## 可用工具

- 查询工具：了解布局细节、视觉对象信息、可用资源
- 操作工具：将设计应用到预览、添加文本元素、加载 Skill
- 外部工具（MCP）：搜索设计灵感、获取图标素材等

Available Skills:
{skills_summary}
Use the load_skill tool to load a skill's full instructions when needed.

## 设计规则

1. SVG 尺寸必须与画布尺寸一致
2. 不要包含任何数据图表内容，只设计装饰性背景元素
3. 在动态图表位置留出适当空间
4. 考虑整体的视觉平衡和色彩协调
5. 输出 SVG 时使用 apply_design 工具应用到预览
```

用户 prompt 包含布局摘要、布局模式、元素信息等上下文数据。

### 图片上传与风格识别

**对话面板支持用户上传参考图片**（PNG/JPG/SVG），用于向 AI 传达风格偏好。

**处理流程：**

1. 用户通过对话面板的上传按钮选择图片
2. 工具将图片以 base64 编码附加到 API 请求的 `content` 中（Claude 多模态输入）
3. AI 分析图片并提取风格特征：
   - 主色调和辅助色
   - 设计风格（扁平/拟物/极简/渐变等）
   - 装饰元素类型（线条/色块/纹理/图标风格）
   - 整体氛围（商务/活泼/科技/自然等）
4. AI 将风格分析结果作为设计依据

**模型兼容性检查：**

| 模型 | 多模态支持 | 处理 |
|------|-----------|------|
| claude-sonnet-4-6 | ✅ 支持 | 正常发送图片 |
| claude-opus-4 | ✅ 支持 | 正常发送图片 |
| claude-haiku-4-5 | ✅ 支持 | 正常发送图片 |
| 不支持视觉的模型 | ❌ | 用户上传图片时提示：「当前模型不支持图片分析，请切换到支持视觉的模型（如 claude-sonnet-4-6）」 |

**UI 交互：**
- 对话输入框旁增加 📎 附件按钮，支持选择图片文件
- 图片缩略图显示在对话面板中
- 拖拽图片到对话面板也可直接上传

### 响应解析

从流式响应中处理内容：
- `text` 类型 → 追加到对话面板显示
- `tool_use` 类型 → 执行对应工具，将结果作为 `tool_result` 发回
- `input_json_delta` 中的 SVG 代码 → 检测 `<svg>` 开始和 `</svg>` 结束，提取完整 SVG
- 验证 SVG 格式有效性
- 解析为 QGraphicsItem 列表渲染到画布

## 原有装饰元素处理

.pbix 中已有的非动态元素（shape、image、textbox）作为「原始素材」保留在对象列表中：

- 默认全部勾选导出
- 用户可以逐个取消勾选（比如去掉不需要的旧装饰）
- AI 设计时可以选择复用（参考现有风格）或完全重新设计
- 如果 AI 设计的新元素与原始元素位置重叠，用户通过勾选控制保留哪个

## 模拟图表渲染（mock_renderer.py）

### 支持的图表类型

| visualType | 模拟样式 |
|-----------|---------|
| donutChart | 环形图：3~5 段彩色圆弧 + 中心空白 |
| pieChart | 饼图：3~5 段彩色扇形 |
| lineChart | 折线图：坐标轴 + 1~2 条随机折线 |
| hundredPercentStackedBarChart | 堆叠条形图：水平堆叠色条 |
| lineClusteredColumnComboChart | 组合图：柱状 + 折线叠加 |
| tableEx | 表格：表头 + 网格线 + 模拟文字色块 |
| pivotTable | 透视表：带分组缩进的表格 |
| cardVisual | 数据卡片：大数字 + 小标签 |
| Gantt / powerGANTTchart | 甘特图：时间轴 + 彩色横条 |
| slicer / advancedSlicerVisual | 筛选器：圆角标签块 |
| htmlContent | HTML 内容区：虚线边框 + 标识 |
| synopticPanel | 地图面板：虚线边框 + 标识 |

### 模拟数据生成

- 从 config 的 `queryState` 或 `prototypeQuery` 提取结构信息（度量数量、分类字段数量）
- 用字段名的哈希值作为随机种子 → 同一图表每次打开数据一致，不同图表数据不同
- 数值范围根据图表类型自适应

### 颜色方案

使用 Power BI 默认调色板近似色：
```python
MOCK_COLORS = [
    "#01B8AA",  # 青绿
    "#374649",  # 深灰
    "#FD6252",  # 珊瑚红
    "#F2C80F",  # 金黄
    "#5F6B6D",  # 灰蓝
    "#8AD4EB",  # 浅蓝
    "#FE9666",  # 橙色
    "#A66999",  # 紫色
]
```

## 导出规则

### 导出内容

导出图 = AI 设计层（可勾选） + 文本层（可勾选+可编辑）

- AI 设计元素：默认导出，可取消勾选
- 文本元素（textbox + 图表标题）：默认导出，可取消勾选，可编辑文字
- 动态图表：永不导出，仅预览参考

### 导出格式

- PNG：与画布等尺寸（如 1280×720），无损
- SVG：矢量格式，可无限缩放

### 文件命名

`{页面displayName}_background.png` / `{页面displayName}_background.svg`

## 用户界面

### 主窗口布局

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  PBI-BgDesign                                                               │
│  打开文件: [xxx.pbix ▼]    当前页面: [PageName ▼]                            │
│  布局模式: [● 固定 ○ 弹性 ○ 自由]   Skills: 3 个已加载    [👁] [AI设计] [导出] │
├──────────┬─────────────────────────────────────┬────────────────────────────┤
│          │                                     │  💬 AI 对话                 │
│ 页面列表  │          画布预览区域                  │                            │
│          │                                     │  AI: 已根据布局生成设计，   │
│ ▶ Home   │  ┌─────────────────────────────┐   │  采用蓝色商务风格...        │
│   Site_  │  │                             │   │                            │
│   Overview│ │  AI 设计 + 模拟图表 + 文本    │   │  你: 分隔条颜色换深灰，     │
│   ...    │  │  滚轮缩放、拖拽平移          │   │  卡片加圆角                 │
│          │  │  悬停高亮、点击选择           │   │                            │
│          │  └─────────────────────────────┘   │  AI: 已调整，请查看预览     │
│          │                                     │  ──────────────────────    │
│          │                                     │  [📎] [输入反馈...]    [发送] │
├──────────┴─────────────────────────────────────┴────────────────────────────┤
│ 视觉对象列表（当前页：Home）                                                   │
│ ┌──────────────────────────────────────────────────────────────────────┐   │
│ │ ☑ [AI设计] 顶部装饰条          x:0    y:64   w:1280  h:22           │   │
│ │ ☑ [文本]  标题 "Home Report"   x:27   y:7    w:473   h:78           │   │
│ │ ▼ [合成组 1] 环形图区域（3个元素叠加）                                │   │
│ │     ☑ [标题]  "产品分布"                                             │   │
│ │       [图表]  环形图 donutChart  (仅预览，不导出)                      │   │
│ │       [图表]  卡片 "总计"       (仅预览，不导出)                      │   │
│ └──────────────────────────────────────────────────────────────────────┘   │
│  [全选装饰] [全不选] [反选]                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

右侧对话面板可通过按钮折叠/展开。

### 交互说明

| 操作 | 行为 |
|------|------|
| 点击左侧页面名 | 切换画布预览，刷新对象列表 |
| 勾选/取消对象 | 画布实时更新显示/隐藏 |
| 双击文本项 | 进入文字编辑模式 |
| 鼠标悬停画布对象 | 对象高亮，列表对应行高亮 |
| 点击画布对象 | 切换该对象勾选状态 |
| Ctrl+滚轮 | 缩放画布 |
| 拖拽画布空白处 | 平移画布 |
| 点击 📎 或拖拽图片到对话面板 | 上传参考图片供 AI 分析风格 |
| 对话面板中点击图片缩略图 | 放大预览该图片 |

### 全屏预览

- F11 或点击 👁 按钮进入
- 白色画布背景，按原始比例居中
- 控制栏半透明浮层，几秒无操作自动隐藏
- ← → 方向键切换页面
- ESC 退出全屏

### 合成组交互

- 重叠元素自动归组，用彩色虚线框标注
- 组可展开/折叠
- 可手动拆分组（右键 → 拆分组）
- 可手动合并组（选中多个 → 右键 → 合并为组）

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| .pbix 文件损坏或格式不对 | 提示错误信息，建议重新导出 |
| Layout JSON 解析失败 | 提示具体解析错误位置 |
| 资源文件缺失 | 跳过该资源，画布上显示占位标记 |
| 图表 config 无法解析 | 归为"未知类型"，显示为灰色矩形 |
| API Key 未配置或无效 | 引导用户到设置面板配置 API Key |
| API 调用失败（网络/限流） | 显示错误信息，提供重试按钮 |
| API 返回的 SVG 格式无效 | 提示 AI 重新生成，最多重试 3 次 |
| API token 消耗过大 | 设置面板中显示本次会话用量，可设置单次上限 |
| 上传图片但模型不支持视觉 | 提示用户切换到支持视觉的模型（如 claude-sonnet-4-6） |
| 上传图片文件过大（>10MB） | 提示压缩后重试，或自动压缩到合理尺寸 |
| 上传图片格式不支持 | 仅支持 PNG/JPG/SVG，其他格式提示不支持 |

## Power BI 外部工具集成

工具同时支持两种启动方式：独立运行 + Power BI 外部工具。

### 注册为 Power BI External Tool

安装时自动写入 Windows 注册表：

```
HKEY_CURRENT_USER\Software\Microsoft\Power BI Desktop\External Tools\PBI-BgDesign\
    DisplayName = "PBI 背景设计"
    Description = "为报表页设计美观的背景图和装饰元素"
    Path = "{安装目录}\pbi-bgdesign.exe"
    Arguments = "%pbi%"
    Icon = "{安装目录}\icon.ico
```

注册后，Power BI Desktop 的「外部工具」选项卡中会出现 PBI-BgDesign 的按钮。

### 命令行参数处理

```python
# app.py 启动时检查命令行参数
import sys

if len(sys.argv) > 1:
    pbix_path = sys.argv[1]
    # 从 Power BI 外部工具启动 → 自动加载该文件
else:
    pbix_path = None
    # 独立启动 → 弹出文件选择对话框
```

### 两种入口的流程对比

| 方式 | 启动来源 | 文件加载 | 用户操作 |
|------|---------|---------|---------|
| 外部工具 | Power BI 点击按钮 | 自动加载命令行传入的临时 .pbix | 零操作，直接进入设计 |
| 独立运行 | 桌面快捷方式/开始菜单 | 弹出文件选择对话框 | 手动选择 .pbix 文件 |

### 注意事项

- Power BI 传入的是临时文件路径（位于 `%TEMP%\pbi\` 目录），包含当前所有修改
- 临时文件在 Power BI 关闭后可能被清理，工具加载后在内存中解析即可
- 工具不修改 .pbix 文件，只读取并导出背景图
