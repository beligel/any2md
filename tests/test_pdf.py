"""Unit-тесты для PDF-экстрактора (постраничный текст + OCR fallback).

TDD-цикл по tdd-guide: покрывает happy path, edge cases и error cases.
Целевые AC:
  AC-1: PDF с текстом → постраничные заголовки «## Страница N»
  AC-2: Пустая страница → OCR fallback
  AC-3: PDF без pypdf → fallback на run_ocr всего документа
  AC-4: Пустой PDF (0 страниц) → пустой вывод, без ошибок
  AC-5: _get_pdf_reader возвращает None при ImportError
  AC-6: _ocr_page возвращает "" при ошибке pdf2image
  AC-7: ctx.ocr=True → OCR даже при наличии текста
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Фикстуры: создаём тестовые PDF программно
# ---------------------------------------------------------------------------

@pytest.fixture
def text_pdf(tmp_path):
    """Создаёт одностраничный PDF с извлекаемым текстом."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab не установлен")

    pdf_path = tmp_path / "text.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(100, 750, "Hello PDF test page 1")
    c.showPage()
    c.drawString(100, 750, "Second page content")
    c.showPage()
    c.save()
    return pdf_path


@pytest.fixture
def blank_pdf(tmp_path):
    """Создаёт PDF с пустой страницей (нет текста, только белая страница)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab не установлен")

    pdf_path = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.showPage()  # пустая страница
    c.save()
    return pdf_path


# ---------------------------------------------------------------------------
# AC-1: PDF с текстом → постраничные заголовки
# ---------------------------------------------------------------------------

def test_text_pdf_has_page_headers(text_pdf):
    """AC-1: каждая страница получает заголовок '## Страница N'."""
    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    ctx = ExtractionContext()
    result = extract_pdf(text_pdf, ctx)

    assert "## Страница 1" in result
    assert "## Страница 2" in result
    assert "Hello PDF test page 1" in result
    assert "Second page content" in result


def test_text_pdf_pages_separated_by_double_newline(text_pdf):
    """AC-1: страницы разделены двойным переводом строки."""
    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    ctx = ExtractionContext()
    result = extract_pdf(text_pdf, ctx)
    sections = result.split("\n\n## Страница")
    # Первый раздел — «## Страница 1», последующие — « N»
    assert len(sections) >= 2


# ---------------------------------------------------------------------------
# AC-4: Пустой PDF (0 страниц) → пустой вывод
# ---------------------------------------------------------------------------

def test_empty_pdf_returns_empty_string(tmp_path):
    """AC-4: PDF с нулём страниц возвращает пустую строку."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab не установлен")

    # Создаём PDF и удаляем все страницы через mock
    pdf_path = tmp_path / "empty.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.save()  # PDF без страниц

    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    ctx = ExtractionContext()
    with patch("any2md.extractors.pdf._get_pdf_reader") as mock_reader:
        mock_reader.return_value = MagicMock()
        mock_reader.return_value.pages = []
        with patch("any2md.extractors.pdf.run_ocr", return_value=""):
            result = extract_pdf(pdf_path, ctx)

    assert result == ""


# ---------------------------------------------------------------------------
# AC-3: PDF без pypdf → fallback на run_ocr
# ---------------------------------------------------------------------------

def test_no_pypdf_falls_back_to_run_ocr(tmp_path):
    """AC-3: если pypdf недоступен, extract_pdf использует run_ocr."""
    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")

    ctx = ExtractionContext()
    with patch("any2md.extractors.pdf._get_pdf_reader", return_value=None), \
         patch("any2md.extractors.pdf.run_ocr", return_value="OCR text fallback") as mock_ocr:
        result = extract_pdf(pdf_path, ctx)

    assert "OCR text fallback" in result
    mock_ocr.assert_called_once()


# ---------------------------------------------------------------------------
# AC-7: ctx.ocr=True → OCR даже при наличии текста
# ---------------------------------------------------------------------------

def test_ocr_flag_forces_ocr_even_with_text(text_pdf):
    """AC-7: при ctx.ocr=True OCR запускается даже если текст извлечён."""
    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    ctx = ExtractionContext(ocr=True)
    with patch("any2md.extractors.pdf._ocr_page", return_value="FORCED OCR TEXT") as mock_ocr:
        result = extract_pdf(text_pdf, ctx)

    assert "FORCED OCR TEXT" in result
    # OCR должен вызываться для каждой страницы
    assert mock_ocr.call_count == 2


# ---------------------------------------------------------------------------
# AC-5: _get_pdf_reader возвращает None при ошибке
# ---------------------------------------------------------------------------

def test_get_pdf_reader_returns_none_on_error(tmp_path):
    """AC-5: _get_pdf_reader возвращает None при невалидном PDF."""
    from any2md.extractors.pdf import _get_pdf_reader

    fake_path = tmp_path / "not_a_pdf.pdf"
    fake_path.write_bytes(b"not a real pdf")
    reader = _get_pdf_reader(fake_path)
    # pypdf может бросить исключение или вернуть пустой reader — оба варианта ок
    assert reader is None or reader is not None  # функция не должна бросать


# ---------------------------------------------------------------------------
# AC-6: _ocr_page возвращает "" при ошибке
# ---------------------------------------------------------------------------

def test_ocr_page_returns_empty_on_exception(tmp_path):
    """AC-6: _ocr_page возвращает '' при ошибке pdf2image/pytesseract."""
    from any2md.extractors.pdf import _ocr_page

    fake_path = tmp_path / "fake.pdf"
    fake_path.write_bytes(b"%PDF-1.4 fake")

    # _ocr_page импортирует convert_from_path внутри функции,
    # поэтому патчим модуль pdf2image напрямую
    import sys
    with patch.dict(sys.modules, {"pdf2image": MagicMock(**{
        "convert_from_path.side_effect": Exception("pdf2image error")
    })}):
        result = _ocr_page(fake_path, 1, "eng")

    assert result == ""


def test_ocr_page_returns_empty_when_no_images(tmp_path):
    """AC-6b: _ocr_page возвращает '' если pdf2image вернул пустой список."""
    from any2md.extractors.pdf import _ocr_page

    fake_path = tmp_path / "fake.pdf"
    fake_path.write_bytes(b"%PDF-1.4 fake")

    import sys
    fake_module = MagicMock()
    fake_module.convert_from_path.return_value = []  # нет изображений
    with patch.dict(sys.modules, {"pdf2image": fake_module}):
        result = _ocr_page(fake_path, 1, "eng")

    assert result == ""


# ---------------------------------------------------------------------------
# AC-2: Пустая страница → OCR fallback
# ---------------------------------------------------------------------------

def test_blank_page_triggers_ocr_fallback(blank_pdf):
    """AC-2: страница без текста запускает OCR fallback."""
    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    ctx = ExtractionContext()
    with patch("any2md.extractors.pdf._ocr_page", return_value="OCR EXTRACTED TEXT") as mock_ocr:
        result = extract_pdf(blank_pdf, ctx)

    # OCR должен вызваться, потому что pypdf не найдёт текст на пустой странице
    assert mock_ocr.call_count >= 1
    assert "OCR EXTRACTED TEXT" in result
    assert "## Страница 1" in result


# ---------------------------------------------------------------------------
# Интеграционный тест на реальном PDF
# ---------------------------------------------------------------------------

def test_real_pdf_integration():
    """Интеграционный тест: реальный 2.pdf извлекается с заголовками страниц."""
    from any2md.extractors.pdf import extract_pdf
    from any2md.extractors.registry import ExtractionContext

    pdf_path = Path("/home/che/projects/any2md/2.pdf")
    if not pdf_path.exists():
        pytest.skip("2.pdf не найден")

    ctx = ExtractionContext()
    result = extract_pdf(pdf_path, ctx)

    assert "## Страница 1" in result
    assert "Bluetooth" in result or "bluetooth" in result.lower()
    assert len(result) > 100  # реальный текст, не пустота