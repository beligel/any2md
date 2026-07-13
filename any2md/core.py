"""Ядро any2md — конвертация файлов и директорий в Markdown."""

import logging
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable, Optional, Union

from tqdm import tqdm

from .extractors.archive import _ARCHIVE_FORMATS, _extract_archive
from .extractors.media import _AUDIO_VIDEO_EXTENSIONS
from .extractors.openoffice_ebook import _EBOOK_OPENOFFICE_EXTENSIONS
from .extractors.registry import ExtractionContext, get_extractor
from .utils import ensure_dir, get_mime_type, is_binary, maybe_decode

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (
    ".txt", ".md", ".html", ".htm", ".csv", ".json", ".xml",
    ".docx", ".xlsx", ".pptx",
    ".pdf",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
) + _ARCHIVE_FORMATS + _AUDIO_VIDEO_EXTENSIONS + _EBOOK_OPENOFFICE_EXTENSIONS


def _path_to_output(input_path: Path, output_dir: Path, keep_relative: bool = True, root: Path | None = None) -> Path:
    """Формирует путь к выходному .md внутри output_dir."""
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
    stdout: bool = False,
) -> Path:
    content = _extract_or_decode(file_path, ctx)
    if stdout:
        sys.stdout.write(content)
        return file_path
    out_path = _path_to_output(file_path, output_dir, keep_relative=keep_relative, root=root)
    out_path.write_text(content, encoding="utf-8")
    logger.info("Сконвертировано: %s -> %s", file_path, out_path)
    return out_path


def _collect_files(root: Path, recursive: bool = True) -> Iterable[Path]:
    if recursive:
        return [p for p in root.rglob("*") if p.is_file()]
    return [p for p in root.iterdir() if p.is_file()]


def _is_archive(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in _ARCHIVE_FORMATS or path.name.lower().endswith(tuple(_ARCHIVE_FORMATS))


def _is_supported(path: Path, mime: Optional[str] = None) -> bool:
    """Определяет, поддерживается ли файл — по расширению или MIME."""
    if path.suffix.lower() in SUPPORTED_SUFFIXES:
        return True
    if path.name.lower().endswith(tuple(_ARCHIVE_FORMATS)):
        return True
    if mime and get_extractor(path, mime=mime) is not None:
        return True
    return False


def _extract_or_decode(file_path: Path, ctx: ExtractionContext) -> str:
    """Извлекает текст из файла или декодирует как текст."""
    mime = get_mime_type(file_path)
    extractor = get_extractor(file_path, mime=mime)
    if extractor is None:
        if is_binary(file_path):
            return f"*Бинарный файл пропущен:* `{file_path.name}`"
        return maybe_decode(file_path, ctx.encoding)
    return extractor(file_path, ctx)


def _process_archive_single(
    archive_path: Path,
    output_dir: Path,
    ctx: ExtractionContext,
    root: Path | None = None,
) -> list[Path]:
    """Раскрывает один архив и конвертирует содержимое относительно папки архива."""
    results: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="any2md_archive_") as tmp:
        tmp_path = Path(tmp)
        try:
            _extract_archive(archive_path, tmp_path)
            # Определяем базовую папку внутри архива (если в корне один элемент — используем его содержимое)
            top_level = [p for p in tmp_path.iterdir() if p.name not in {"__MACOSX"}]
            if len(top_level) == 1 and top_level[0].is_dir():
                base = top_level[0]
            else:
                base = tmp_path

            for inner in _collect_files(base, recursive=True):
                if not _is_supported(inner, mime=get_mime_type(inner)):
                    continue
                rel = inner.relative_to(base)
                # Маппим внутренний файл относительно папки архива, а не temp dir
                if root and archive_path.is_relative_to(root):
                    target = output_dir / archive_path.relative_to(root).parent / rel.with_suffix(".md")
                else:
                    target = output_dir / archive_path.stem / rel.with_suffix(".md")
                ensure_dir(target.parent)
                content = _extract_or_decode(inner, ctx)
                target.write_text(content, encoding="utf-8")
                logger.info("Сконвертировано: %s (из архива %s) -> %s", inner, archive_path, target)
                results.append(target)
        except Exception as exc:
            logger.warning("Не удалось раскрыть архив %s: %s", archive_path, exc)
    return results


def _process_archives(files: Iterable[Path], output_dir: Path, ctx: ExtractionContext, root: Path | None = None) -> list[Path]:
    extra: list[Path] = []
    for path in files:
        if _is_archive(path):
            extra.extend(_process_archive_single(path, output_dir, ctx, root=root))
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
    stdout: bool = False,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Union[Path, list[Path], None]:
    """Конвертирует файл или директорию в Markdown.

    Returns:
        Path — для одного файла, list[Path] — для директории,
        None — если stdout=True.
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
        # Архив конвертируется как набор вложенных файлов
        if _is_archive(input_path):
            archive_dir = Path(output_path).resolve() if output_path else input_path.parent
            ensure_dir(archive_dir)
            return sorted(_process_archive_single(input_path, archive_dir, ctx))

        if stdout:
            _convert_single_file(input_path, Path.cwd(), ctx, keep_relative=False, stdout=True)
            return None

        if output_path is None:
            output_path = input_path.with_suffix(".md")
        output_path = Path(output_path).resolve()
        ensure_dir(output_path.parent)
        out = output_path
        content = _extract_or_decode(input_path, ctx)
        out.write_text(content, encoding="utf-8")
        logger.info("Сконвертировано: %s -> %s", input_path, out)
        return out

    if input_path.is_dir():
        output_dir = Path(output_path).resolve() if output_path else input_path.parent / (input_path.name + "_md")
        ensure_dir(output_dir)
        files = list(_collect_files(input_path, recursive=recursive))

        results: list[Path] = []
        archives: list[Path] = []
        skipped: list[Path] = []

        def handle(path: Path) -> Optional[Path]:
            if _is_archive(path):
                archives.append(path)
                return None
            mime = get_mime_type(path)
            if not _is_supported(path, mime=mime):
                skipped.append(path)
                logger.debug("Пропуск неподдерживаемого файла: %s", path)
                return None
            return _convert_single_file(path, output_dir, ctx, keep_relative=True, root=input_path)

        for f in files:
            if _is_archive(f):
                archives.append(f)

        file_list = [f for f in files if not _is_archive(f)]
        total_files = len(file_list)

        with tqdm(total=total_files, desc="Конвертация", unit="файл", disable=total_files <= 1) as pbar:
            def progress_hook(current: int, total: int):
                pbar.n = current
                pbar.total = total
                pbar.refresh()
                if progress_callback:
                    progress_callback(current, total)

            def wrapped_handle(path: Path) -> Optional[Path]:
                result = handle(path)
                pbar.update(1)
                if progress_callback:
                    progress_callback(pbar.n, total_files)
                return result

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(wrapped_handle, f): f for f in file_list}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)

        if archives:
            logger.info("Обработка архивов: %s", [str(a) for a in archives])
            archive_results = _process_archives(archives, output_dir, ctx, root=input_path)
            results.extend(archive_results)

        return sorted(results)

    raise FileNotFoundError(input_path)
