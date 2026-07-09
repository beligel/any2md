"""Экстракторы для OpenDocument, FictionBook 2 и EPUB."""

from pathlib import Path
from zipfile import ZipFile

from .registry import ExtractionContext, register_extractor

_EBOOK_OPENOFFICE_EXTENSIONS = (
    ".odt", ".ods", ".odp",
    ".fb2",
    ".epub",
)


def _xml_text_from_zip(path: Path, xml_path: str) -> str:
    """Извлекает текст из XML-файла внутри zip-based документа."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("Для разбора XML нужно установить beautifulsoup4")

    with ZipFile(path, "r") as zf:
        if xml_path not in zf.namelist():
            return ""
        xml_bytes = zf.read(xml_path)

    soup = BeautifulSoup(xml_bytes, "xml")
    # Удаляем лишние теги, оставляем текст
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


@register_extractor(".odt")
@register_extractor("application/vnd.oasis.opendocument.text")
@register_extractor(".ods")
@register_extractor("application/vnd.oasis.opendocument.spreadsheet")
@register_extractor(".odp")
@register_extractor("application/vnd.oasis.opendocument.presentation")
def extract_opendocument(path: Path, ctx: ExtractionContext) -> str:
    content = _xml_text_from_zip(path, "content.xml")
    return f"# {path.name}\n\n{content}" if content.strip() else content


@register_extractor(".fb2")
@register_extractor("application/fb2+xml")
@register_extractor("application/x-fictionbook+xml")
def extract_fb2(path: Path, ctx: ExtractionContext) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("Для .fb2 нужно установить beautifulsoup4")

    text = path.read_bytes()
    soup = BeautifulSoup(text, "xml")
    # В FB2 текст обычно внутри <body>, <section>, <p>
    for tag in soup.find_all(["binary"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


@register_extractor(".epub")
@register_extractor("application/epub+zip")
def extract_epub(path: Path, ctx: ExtractionContext) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("Для .epub нужно установить beautifulsoup4")

    parts = []
    with ZipFile(path, "r") as zf:
        namelist = zf.namelist()
        # Определяем порядок HTML-файлов по OPF
        opf_files = [n for n in namelist if n.endswith(".opf")]
        html_order = []
        if opf_files:
            opf = zf.read(opf_files[0])
            opf_soup = BeautifulSoup(opf, "xml")
            for item in opf_soup.find_all("item"):
                href = item.get("href")
                media_type = item.get("media-type", "")
                if href and "html" in media_type:
                    # относительный путь от OPF
                    opf_dir = Path(opf_files[0]).parent.as_posix()
                    target = (opf_dir + "/" + href).strip("/") if opf_dir else href
                    html_order.append(target)

        if not html_order:
            html_order = sorted(n for n in namelist if n.endswith((".html", ".xhtml", ".htm")))

        for name in html_order:
            if name not in namelist:
                continue
            html = zf.read(name)
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup.find_all(["script", "style", "nav"]):
                tag.decompose()
            body_text = soup.get_text("\n", strip=True)
            if body_text:
                parts.append(body_text)

    return "\n\n".join(parts)
