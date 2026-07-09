"""Утилиты any2md."""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def maybe_decode(path: Path, encoding: str = "utf-8") -> str:
    raw = path.read_bytes()
    for enc in (encoding, "utf-8", "windows-1251", "cp1252", "latin-1", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def run_ocr(path: Path, lang: str = "eng") -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("OCR недоступен: установите pytesseract и Pillow")
        return ""

    try:
        image = Image.open(path)
        return pytesseract.image_to_string(image, lang=lang).strip()
    except Exception as exc:
        logger.warning("OCR не удался для %s: %s", path, exc)
        return ""


def get_mime_type(path: Path) -> str:
    try:
        import magic
        return magic.from_file(str(path), mime=True)
    except Exception:
        return ""


def is_binary(path: Path) -> bool:
    """Простая эвристика бинарности по нулевому байту."""
    chunk = path.read_bytes()[:8192]
    return b"\x00" in chunk


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
