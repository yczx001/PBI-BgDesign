"""AI design engine using Claude API with streaming and tool use."""
from PyQt6.QtCore import QObject, pyqtSignal
import json

import anthropic

from pbi_bgdesign.ai.skills import SkillLoader
from pbi_bgdesign.layout_analyzer import LayoutAnalysis, generate_layout_summary

SUPPORTED_VISION_MODELS = {
    "claude-sonnet-4-6",
    "claude-opus-4",
    "claude-haiku-4-5-20251001",
}


def build_system_prompt(skills_summary: str) -> str:
    return f"""你是一个 Power BI 报表背景设计师。你的任务是根据报表布局信息设计美观的背景和装饰元素。

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

{skills_summary}

## 设计规则

1. SVG 尺寸必须与画布尺寸一致
2. 不要包含任何数据图表内容，只设计装饰性背景元素
3. 在动态图表位置留出适当空间
4. 考虑整体的视觉平衡和色彩协调
5. 输出 SVG 时使用 apply_design 工具应用到预览"""


def build_tool_definitions() -> list[dict]:
    return [
        {
            "name": "get_layout_info",
            "description": "获取指定页面的完整布局数据",
            "input_schema": {
                "type": "object",
                "properties": {
                    "page_name": {"type": "string", "description": "页面名称"}
                },
                "required": ["page_name"]
            }
        },
        {
            "name": "get_visual_details",
            "description": "获取某个视觉对象的完整 config（标题、样式、数据字段等）",
            "input_schema": {
                "type": "object",
                "properties": {
                    "visual_id": {"type": "string", "description": "视觉对象 ID"}
                },
                "required": ["visual_id"]
            }
        },
        {
            "name": "get_overlap_groups",
            "description": "获取重叠分组的详细信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "page_name": {"type": "string", "description": "页面名称"}
                },
                "required": ["page_name"]
            }
        },
        {
            "name": "list_resources",
            "description": "列出 .pbix 中可用的图片资源",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "apply_design",
            "description": "将 SVG 设计应用到预览画布",
            "input_schema": {
                "type": "object",
                "properties": {
                    "svg_code": {"type": "string", "description": "完整的 SVG 代码"}
                },
                "required": ["svg_code"]
            }
        },
        {
            "name": "add_text_element",
            "description": "在指定位置添加文本元素",
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                    "font_size": {"type": "number"},
                    "color": {"type": "string"}
                },
                "required": ["text", "x", "y"]
            }
        },
        {
            "name": "highlight_visual",
            "description": "在预览中高亮某个视觉对象",
            "input_schema": {
                "type": "object",
                "properties": {
                    "visual_id": {"type": "string"},
                    "color": {"type": "string"}
                },
                "required": ["visual_id"]
            }
        },
        {
            "name": "load_skill",
            "description": "加载指定 Skill 的完整内容到对话上下文",
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Skill 名称"}
                },
                "required": ["skill_name"]
            }
        },
        {
            "name": "list_skills",
            "description": "列出所有可用的 Skill",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
    ]


class AIDesigner(QObject):
    """AI design engine managing Claude API conversation."""

    # Signals for UI
    text_received = pyqtSignal(str)       # Streaming text chunk
    tool_calling = pyqtSignal(str)         # Tool name being called
    design_applied = pyqtSignal(str)       # SVG code applied
    error_occurred = pyqtSignal(str)       # Error message
    finished = pyqtSignal()                # Response complete

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        super().__init__()
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.skill_loader: SkillLoader | None = None
        self.analysis: LayoutAnalysis | None = None
        self.mode: str = "fixed"
        self.conversation: list[dict] = []
        self.resources: dict[str, bytes] = {}

    def model_supports_vision(self) -> bool:
        return self.model in SUPPORTED_VISION_MODELS

    def set_layout(self, analysis: LayoutAnalysis, mode: str):
        self.analysis = analysis
        self.mode = mode
        self.conversation = []

    def set_skill_loader(self, loader: SkillLoader):
        self.skill_loader = loader

    def _build_initial_messages(self) -> list[dict]:
        if not self.analysis:
            return []
        summary = generate_layout_summary(self.analysis, self.mode)
        return [{"role": "user", "content": f"请为以下页面设计背景:\n\n{summary}"}]

    def _handle_tool(self, name: str, input_data: dict) -> str:
        """Execute a tool call and return the result as a string."""
        if name == "get_layout_info":
            if self.analysis:
                return generate_layout_summary(self.analysis, self.mode)
            return "No layout loaded."

        elif name == "get_visual_details":
            vid = input_data.get("visual_id", "")
            if self.analysis:
                for v in self.analysis.page.visuals:
                    if v.id == vid:
                        return json.dumps(v.config, indent=2, ensure_ascii=False)
            return f"Visual '{vid}' not found."

        elif name == "get_overlap_groups":
            if self.analysis:
                groups = self.analysis.groups
                result = []
                for g in groups:
                    if len(g.visuals) > 1:
                        names = [f"{v.id}({v.visual_type})" for v in g.visuals]
                        result.append(f"Group {g.id}: {', '.join(names)}")
                return "\n".join(result) if result else "No overlap groups found."
            return "No layout loaded."

        elif name == "list_resources":
            if self.resources:
                return ", ".join(self.resources.keys())
            return "No resources found."

        elif name == "apply_design":
            svg = input_data.get("svg_code", "")
            self.design_applied.emit(svg)
            return "Design applied to preview."

        elif name == "load_skill":
            skill_name = input_data.get("skill_name", "")
            if self.skill_loader:
                content = self.skill_loader.get_skill_content(skill_name)
                if content:
                    return f"Skill loaded:\n\n{content}"
                return f"Skill '{skill_name}' not found."
            return "No skill loader configured."

        elif name == "list_skills":
            if self.skill_loader:
                return self.skill_loader.get_summary()
            return "No skills available."

        elif name == "add_text_element":
            # Stub: to be implemented when UI integration is complete
            return f"Text element added: '{input_data.get('text', '')}' at ({input_data.get('x', 0)}, {input_data.get('y', 0)})"

        elif name == "highlight_visual":
            # Stub: to be implemented when UI integration is complete
            return f"Highlighted visual: {input_data.get('visual_id', '')}"

        return f"Unknown tool: {name}"

    def start_design(self):
        """Start a new design conversation."""
        self.conversation = self._build_initial_messages()
        self._call_api()

    def send_message(self, text: str, image_data: bytes | None = None, image_type: str | None = None):
        """Send a user message (with optional image) and get AI response."""
        content: list[dict] | str
        if image_data and image_type:
            import base64
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_type,
                        "data": base64.b64encode(image_data).decode("utf-8"),
                    }
                },
                {"type": "text", "text": text}
            ]
        else:
            content = text

        self.conversation.append({"role": "user", "content": content})
        self._call_api()

    def _call_api(self):
        """Call Claude API with streaming and handle tool use loop."""
        skills_summary = self.skill_loader.get_summary() if self.skill_loader else "No skills available."
        system = build_system_prompt(skills_summary)
        tools = build_tool_definitions()

        try:
            while True:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=8192,
                    system=system,
                    messages=self.conversation,
                    tools=tools,
                ) as stream:
                    for event in stream:
                        # Handle text delta
                        if hasattr(event, 'type'):
                            if event.type == "content_block_delta":
                                delta = event.delta
                                if hasattr(delta, 'text') and delta.text:
                                    self.text_received.emit(delta.text)
                                elif hasattr(delta, 'partial_json') and delta.partial_json:
                                    pass  # Tool input streaming

                    # Get the final message
                    message = stream.get_final_message()
                    assistant_content = list(message.content)

                self.conversation.append({"role": "assistant", "content": assistant_content})

                # Check for tool use
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        self.tool_calling.emit(block.name)
                        result = self._handle_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                if not tool_results:
                    break  # No more tool calls, conversation turn complete

                self.conversation.append({"role": "user", "content": tool_results})

        except anthropic.APIError as e:
            self.error_occurred.emit(f"API error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"Error: {e}")
        finally:
            self.finished.emit()
