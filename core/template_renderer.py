import os
from typing import Any, Dict, Optional
from loguru import logger

class TemplateRenderer:
    def __init__(self, templates_dir: str = "data/rag_docs/templates"):
        self.templates_dir = templates_dir
        os.makedirs(self.templates_dir, exist_ok=True)

    def list_templates(self) -> list:
        """List available templates."""
        return [f for f in os.listdir(self.templates_dir) if f.endswith(".md")]

    def render(self, template_name: str, **kwargs) -> str:
        """Render a template by replacing placeholders with values."""
        if not template_name.endswith(".md"):
            template_name += ".md"
            
        file_path = os.path.join(self.templates_dir, template_name)
        if not os.path.exists(file_path):
            logger.warning(f"Template {template_name} not found in {self.templates_dir}")
            return ""

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Simple placeholder replacement: {{ key }}
            for key, value in kwargs.items():
                placeholder = f"{{{{ {key} }}}}"
                content = content.replace(placeholder, str(value))
            
            return content
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            return ""

    def render_auto(self, data: Dict[str, Any]) -> str:
        """Heuristically choose a template based on data and render it."""
        # This is a basic implementation that can be expanded
        if data.get("type") == "academic":
            return self.render("academic_paper_template.md", **data)
        elif data.get("type") == "alpha_note" or "hypothesis" in data:
            return self.render("alpha_note_template.md", **data)
        elif data.get("type") == "macro":
            return self.render("macro_news_template.md", **data)
        elif data.get("type") == "market_meta":
            return self.render("market_meta_yearly_template.md", **data)
        
        return str(data)
