"""Экстрактор для изображений (OCR + базовое описание)."""

from pathlib import Path

from ..utils import run_ocr
from .registry import ExtractionContext, register_extractor


@register_extractor("image/*")
@register_extractor(".png")
@register_extractor(".jpg")
@register_extractor(".jpeg")
@register_extractor(".gif")
@register_extractor(".bmp")
@register_extractor(".tiff")
@register_extractor(".webp")
def extract_image(path: Path, ctx: ExtractionContext) -> str:
    parts = []
    if ctx.image_desc:
        parts.append(f"*Изображение:* `{path.name}`")
    if ctx.ocr:
        text = run_ocr(path, ctx.ocr_lang)
        if text.strip():
            parts.append(text.strip())
    if not parts:
        parts.append(f"![{path.name}]({path.name})")
    return "\n\n".join(parts)
