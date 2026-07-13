"""Unit-тесты для office-экстрактора."""

from pathlib import Path

import pytest

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

from any2md.extractors.office import extract_docx
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
