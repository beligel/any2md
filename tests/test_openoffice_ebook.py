"""Unit-тесты для OpenDocument, FB2 и EPUB экстракторов."""

import zipfile
from pathlib import Path

from any2md.extractors.openoffice_ebook import extract_epub, extract_fb2, extract_opendocument
from any2md.extractors.registry import ExtractionContext, get_extractor


def _make_odt(path: Path, text: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zf.writestr(
            "content.xml",
            f"""<?xml version="1.0" encoding="UTF-8"?>
            <office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
                                      xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
              <office:body>
                <text:p>{text}</text:p>
              </office:body>
            </office:document-content>""",
        )


def test_extract_opendocument(tmp_path):
    src = tmp_path / "doc.odt"
    _make_odt(src, "Привет из OpenDocument")
    result = extract_opendocument(src, ExtractionContext())
    assert "Привет из OpenDocument" in result


def test_extract_fb2(tmp_path):
    src = tmp_path / "book.fb2"
    src.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
        <FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
          <body>
            <section>
              <p>Привет из FB2</p>
            </section>
          </body>
        </FictionBook>""",
        encoding="utf-8",
    )
    result = extract_fb2(src, ExtractionContext())
    assert "Привет из FB2" in result


def test_extract_epub(tmp_path):
    src = tmp_path / "book.epub"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="2.0">
              <manifest>
                <item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
              </manifest>
            </package>""",
        )
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            """<?xml version="1.0"?>
            <html xmlns="http://www.w3.org/1999/xhtml">
              <body>
                <p>Привет из EPUB</p>
              </body>
            </html>""",
        )

    result = extract_epub(src, ExtractionContext())
    assert "Привет из EPUB" in result


def test_extensions_registered():
    for ext in [".odt", ".ods", ".odp", ".fb2", ".epub"]:
        assert get_extractor(Path(f"book{ext}")) is not None, f"no extractor for {ext}"
