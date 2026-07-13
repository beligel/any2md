"""Unit-тесты для office-экстрактора."""

from pathlib import Path

import pytest

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from pptx import Presentation
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

try:
    import openpyxl
    HAS_XLSX = True
except ImportError:
    HAS_XLSX = False

from any2md.extractors.office import extract_docx, extract_pptx, extract_xlsx
from any2md.extractors.registry import ExtractionContext


@pytest.mark.skipif(not HAS_DOCX, reason="python-docx не установлен")
def test_docx_heading_and_bold(tmp_path):
    doc = docx.Document()
    doc.add_heading("Заголовок 1", level=1)
    p = doc.add_paragraph()
    p.add_run("жирный").bold = True
    p.add_run(" и ")
    p.add_run("курсив").italic = True

    src = tmp_path / "test.docx"
    doc.save(src)

    ctx = ExtractionContext()
    text = extract_docx(src, ctx)
    assert "# Заголовок 1" in text
    assert "**жирный**" in text
    assert "*курсив*" in text


@pytest.mark.skipif(not HAS_DOCX, reason="python-docx не установлен")
def test_docx_empty_paragraph_skipped(tmp_path):
    """AC: пустые параграфы не попадают в вывод."""
    doc = docx.Document()
    doc.add_paragraph("   ")
    doc.add_paragraph("Реальный текст")

    src = tmp_path / "test.docx"
    doc.save(src)

    ctx = ExtractionContext()
    text = extract_docx(src, ctx)
    assert "Реальный текст" in text
    assert text.strip().count("\n\n") == 0  # только один параграф


@pytest.mark.skipif(not HAS_DOCX, reason="python-docx не установлен")
def test_docx_table_markdown(tmp_path):
    """AC: таблицы конвертируются в markdown-таблицы."""
    doc = docx.Document()
    doc.add_paragraph("Текст до таблицы")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Заголовок A"
    table.cell(0, 1).text = "Заголовок B"
    table.cell(1, 0).text = "Ячейка 1"
    table.cell(1, 1).text = "Ячейка 2"

    src = tmp_path / "test.docx"
    doc.save(src)

    ctx = ExtractionContext()
    text = extract_docx(src, ctx)
    assert "| Заголовок A | Заголовок B |" in text
    assert "| Ячейка 1 | Ячейка 2 |" in text


@pytest.mark.skipif(not HAS_PPTX, reason="python-pptx не установлен")
def test_pptx_title_and_notes(tmp_path):
    """AC: заголовок слайда и заметки спикера извлекаются.

    Регрессия: в 0.2.1 extract_pptx был определён дважды —
    старое определение без title/notes перекрывало новое.
    """
    prs = Presentation()
    slide_layout = prs.slide_layouts[0]  # Title Slide
    slide = prs.slides.add_slide(slide_layout)
    title_shape = slide.shapes.title
    title_shape.text = "Заголовок презентации"

    # Заметки спикера
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = "Важные заметки"

    src = tmp_path / "test.pptx"
    prs.save(src)

    ctx = ExtractionContext()
    text = extract_pptx(src, ctx)
    assert "Заголовок презентации" in text
    # AC-2: заметки спикера должны извлекаться
    assert "Важные заметки" in text, (
        "Заметки спикера не извлекаются — "
        "вероятно, активна старая (упрощённая) версия extract_pptx"
    )
    # AC-3: заголовок должен быть выделен как **Заголовок:** (новый формат)
    assert "**Заголовок:**" in text, (
        "Заголовок слайда не отформатирован — "
        "активна старая версия extract_pptx без форматирования title"
    )


@pytest.mark.skipif(not HAS_XLSX, reason="openpyxl не установлен")
def test_xlsx_markdown_table(tmp_path):
    """AC: XLSX конвертируется в markdown-таблицу с разделителем."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Данные"
    ws.append(["Имя", "Возраст"])
    ws.append(["Алиса", 30])
    ws.append(["Боб", 25])

    src = tmp_path / "test.xlsx"
    wb.save(src)

    ctx = ExtractionContext()
    text = extract_xlsx(src, ctx)
    assert "## Лист: Данные" in text
    assert "| Имя | Возраст |" in text
    assert "| Алиса | 30 |" in text
    # Разделитель markdown-таблицы
    assert "---" in text
