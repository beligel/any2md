"""Экстракторы для офисных форматов: DOCX, XLSX, PPTX."""

from pathlib import Path

from .registry import ExtractionContext, register_extractor


@register_extractor(".docx")
@register_extractor("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
def extract_docx(path: Path, ctx: ExtractionContext) -> str:
    try:
        import docx
    except ImportError:
        raise RuntimeError("Для .docx нужно установить python-docx")
    doc = docx.Document(path)
    parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            parts.append("| " + " | ".join(cells) + " |")
    return "\n\n".join(parts)


@register_extractor(".xlsx")
@register_extractor("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
def extract_xlsx(path: Path, ctx: ExtractionContext) -> str:
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("Для .xlsx нужно установить openpyxl")
    wb = openpyxl.load_workbook(path, data_only=True)
    parts = []
    for sheet in wb.worksheets:
        parts.append(f"## Лист: {sheet.title}")
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            continue
        md_rows = ["| " + " | ".join(str(c or "") for c in row) + " |" for row in rows]
        sep = "|" + "|".join([" --- " for _ in rows[0]]) + "|"
        parts.append("\n".join([md_rows[0], sep] + md_rows[1:]))
    return "\n\n".join(parts)


@register_extractor(".pptx")
@register_extractor("application/vnd.openxmlformats-officedocument.presentationml.presentation")
def extract_pptx(path: Path, ctx: ExtractionContext) -> str:
    try:
        from pptx import Presentation
    except ImportError:
        raise RuntimeError("Для .pptx нужно установить python-pptx")
    prs = Presentation(path)
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        parts.append(f"## Слайд {i}")
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                parts.append(shape.text.strip())
    return "\n\n".join(parts)
