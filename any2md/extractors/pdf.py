"""Экстрактор для PDF с постраничным OCR-фолбеком."""

import logging
from pathlib import Path

from ..utils import configure_tesseract, run_ocr
from .registry import ExtractionContext, register_extractor

logger = logging.getLogger(__name__)


@register_extractor(".pdf")
@register_extractor("application/pdf")
def extract_pdf(path: Path, ctx: ExtractionContext) -> str:
    """Извлекает текст из PDF постранично, дополняя OCR при необходимости."""
    configure_tesseract()

    parts = []
    reader = _get_pdf_reader(path)
    total_pages = len(reader.pages) if reader else 0

    if total_pages:
        for idx, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            needs_ocr = ctx.ocr or not page_text
            if needs_ocr:
                ocr_text = _ocr_page(path, idx, ctx.ocr_lang)
                if ocr_text:
                    page_text = ocr_text

            if page_text:
                parts.append(f"## Страница {idx}\n\n{page_text}")
    else:
        # Fallback: OCR всего документа как изображений
        full_text = run_ocr(path, ctx.ocr_lang)
        if full_text:
            parts.append(full_text)

    return "\n\n".join(parts).strip()


def _get_pdf_reader(path: Path):
    """Возвращает pypdf PdfReader, если библиотека доступна."""
    try:
        import pypdf
        return pypdf.PdfReader(str(path))
    except Exception:
        return None


def _ocr_page(path: Path, page_number: int, lang: str) -> str:
    """OCR одной страницы PDF через pdf2image."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(str(path), first_page=page_number, last_page=page_number, dpi=200)
        if not images:
            return ""
        return pytesseract.image_to_string(images[0], lang=lang).strip()
    except Exception as exc:
        logger.warning("OCR для страницы %s не удался: %s", page_number, exc)
        return ""
