"""Ядро any2md — конвертация файлов и директорий в Markdown."""

import logging
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, Optional, Union

from .extractors.archive import _ARCHIVE_FORMATS, _extract_archive
from .extractors.media import _AUDIO_VIDEO_EXTENSIONS
from .extractors.openoffice_ebook import _EBOOK_OPENOFFICE_EXTENSIONS
from .extractors.registry import ExtractionContext, get_extractor
from .utils import ensure_dir, get_mime_type, is_binary

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (
    ".txt", ".md", ".html", ".htm", ".csv", ".json", ".xml",
    ".docx", ".xlsx", ".pptx",
    ".pdf",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
) + _ARCHIVE_FORMATS + _AUDIO_VIDEO_EXTENSIONS + _EBOOK_OPENOFFICE_EXTENSIONS


def _path_to_output(input_path: Path, output_dir: Path, keep_relative: bool = True, root: Path | None = None) -> Path:
    if keep_relative:
        if root and input_path.is_relative_to(root):
            rel = input_path.relative_to(root)
        elif input_path.is_absolute():
            rel = input_path.relative_to(input_path.anchor)
        else:
            rel = input_path
        target = output_dir / rel.with_suffix(".md")
    else:
        target = output_dir / f"{input_path.stem}.md"
    ensure_dir(target.parent)
    return target


def _convert_single_file(
    file_path: Path,
    output_dir: Path,
    ctx: ExtractionContext,
    keep_relative: bool = True,
    root: Path | None = None,
) -> Path:
    mime = get_mime_type(file_path)
    extractor = get_extractor(file_path, mime=mime)

    if extractor is None:
        if is_binary(file_path):
            content = f"*Бинарный файл пропущен:* `{file_path.name}`"
        else:
            content = maybe_decode(file_path, ctx.encoding)
    else:
        content = extractor(file_path, ctx)

    out_path = _path_to_output(file_path, output_dir, keep_relative=keep_relative, root=root)
    out_path.write_text(content, encoding="utf-8")
    logger.info("Сконвертировано: %s -> %s", file_path, out_path)
    return out_path


def _collect_files(root: Path, recursive: bool = True) -> Iterable[Path]:
    if recursive:
        return [p for p in root.rglob("*") if p.is_file()]
    return [p for p in root.iterdir() if p.is_file()]


def _process_archives(files: Iterable[Path], output_dir: Path, ctx: ExtractionContext, root: Path | None = None) -> list[Path]:
    extra: list[Path] = []
    for path in files:
        if path.suffix.lower() in _ARCHIVE_FORMATS or path.name.lower().endswith(
            tuple(_ARCHIVE_FORMATS)
        ):
            with tempfile.TemporaryDirectory(prefix="any2md_archive_") as tmp:
                tmp_path = Path(tmp)
                try:
                    _extract_archive(path, tmp_path)
                    for inner in _collect_files(tmp_path, recursive=True):
                        suffix = inner.suffix.lower()
                        if suffix in SUPPORTED_SUFFIXES or suffix in _ARCHIVE_FORMATS:
                            extra.append(_convert_single_file(inner, output_dir, ctx, keep_relative=True, root=root))
                except Exception as exc:
                    logger.warning("Не удалось раскрыть архив %s: %s", path, exc)
    return extra


def convert(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    recursive: bool = True,
    ocr: bool = False,
    ocr_lang: str = "eng+rus",
    image_desc: bool = False,
    encoding: str = "utf-8",
    workers: int = 4,
    whisper_model: Optional[str] = None,
    language: Optional[str] = None,
) -> Union[Path, list[Path]]:
    """Конвертирует файл или директорию в Markdown.

    Returns:
        Path — для одного файла, list[Path] — для директории.
    """
    input_path = Path(input_path).resolve()
    ctx = ExtractionContext(
        ocr=ocr,
        ocr_lang=ocr_lang,
        image_desc=image_desc,
        encoding=encoding,
        whisper_model=whisper_model,
        language=language,
    )

    if input_path.is_file():
        if output_path is None:
            output_path = input_path.with_suffix(".md")
        output_path = Path(output_path).resolve()
        ensure_dir(output_path.parent)
        return _convert_single_file(input_path, output_path.parent, ctx, keep_relative=False)

    if input_path.is_dir():
        output_dir = Path(output_path).resolve() if output_path else input_path.parent / (input_path.name + "_md")
        ensure_dir(output_dir)
        files = _collect_files(input_path, recursive=recursive)

        results: list[Path] = []
        archives: list[Path] = []

        def handle(path: Path) -> Optional[Path]:
            suffix = path.suffix.lower()
            if suffix in _ARCHIVE_FORMATS or path.name.lower().endswith(tuple(_ARCHIVE_FORMATS)):
                archives.append(path)
                return None
            if suffix not in SUPPORTED_SUFFIXES:
                logger.debug("Пропуск неподдерживаемого файла: %s", path)
                return None
            return _convert_single_file(path, output_dir, ctx, keep_relative=True, root=input_path)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(handle, f): f for f in files}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        if archives:
            results.extend(_process_archives(archives, output_dir, ctx, root=input_path))

        return sorted(results)

    raise FileNotFoundError(input_path)


# re-export для extractors.text
from .utils import maybe_decode  # noqa: E402, F401
