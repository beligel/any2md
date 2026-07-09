"""Экстрактор для архивов — раскрывает текстовые/офисные файлы внутри."""

import shutil
import tempfile
from pathlib import Path

from .registry import ExtractionContext, register_extractor


_ARCHIVE_FORMATS = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")


def _extract_archive(path: Path, dest: Path) -> None:
    shutil.unpack_archive(path, dest)


@register_extractor(".zip")
@register_extractor("application/zip")
@register_extractor(".tar")
@register_extractor("application/x-tar")
@register_extractor(".tar.gz")
@register_extractor(".tgz")
@register_extractor("application/gzip")
@register_extractor(".tar.bz2")
@register_extractor(".tbz2")
@register_extractor("application/x-bzip2")
@register_extractor(".tar.xz")
@register_extractor(".txz")
@register_extractor("application/x-xz")
def extract_archive(path: Path, ctx: ExtractionContext) -> str:
    """Раскрывает архив и конвертирует каждый файл — вызывается из core."""
    return f"*Архив:* `{path.name}` (будет обработан рекурсивно)"
