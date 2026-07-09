"""Экстрактор для PDF с OCR-фолбеком."""

from pathlib import Path

from ..utils import run_ocr
from .registry import ExtractionContext, register_extractor


@register_extractor(".pdf")
@register_extractor("application/pdf")
def extract_pdf(path: Path, ctx: ExtractionContext) -> str:
    try:
        import pypdf
    except ImportError:
        pypdf = None
    text = ""
    if pypdf:
        reader = pypdf.PdfReader(str(path))
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    if ctx.ocr or not text.strip():
        text = run_ocr(path, ctx.ocr_lang)
    return text.strip()
