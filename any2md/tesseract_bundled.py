"""Загрузка и настройка bundled Tesseract OCR.

Системный tesseract-ocr больше не требуется. При первом вызове OCR
any2md скачивает готовые Debian/Ubuntu .deb пакеты и распаковывает
их в папку проекта `.any2md/tesseract/`, если их ещё нет.
"""

import logging
import os
import shutil
import stat
import subprocess
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# Ubuntu 24.04 (noble) amd64 .deb пакеты — стабильные URL.
# Можно заменить на ближайший mirror при необходимости.
UBUNTU_MIRROR = "http://archive.ubuntu.com/ubuntu"

PACKAGES = {
    "libtesseract5": f"{UBUNTU_MIRROR}/pool/universe/t/tesseract/libtesseract5_5.3.4-1build5_amd64.deb",
    "tesseract-ocr": f"{UBUNTU_MIRROR}/pool/universe/t/tesseract/tesseract-ocr_5.3.4-1build5_amd64.deb",
    "liblept5": f"{UBUNTU_MIRROR}/pool/universe/l/leptonlib/liblept5_1.82.0-3build4_amd64.deb",
}

# Языковые данные ставим через Ubuntu .deb пакеты tesseract-ocr-<lang>.
LANGS = ("eng", "rus", "fra", "deu", "spa")


def _base_dir() -> Path:
    return Path(__file__).resolve().parent.parent / ".any2md" / "tesseract"


def _tessdata_dir() -> Path:
    base = _base_dir()
    for sub in ("5", "4.00"):
        candidate = base / "usr" / "share" / "tesseract-ocr" / sub / "tessdata"
        if candidate.exists():
            return candidate
    return base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"


def _binary_path() -> Path:
    return _base_dir() / "usr" / "bin" / "tesseract"


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download(url: str, dest: Path, chunk_size: int = 65536) -> None:
    logger.info("Скачивание %s -> %s", url, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "any2md/0.2.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        expected = response.headers.get("Content-Length")
        data = response.read()
        if expected and int(expected) != len(data):
            raise RuntimeError(f"Неполная загрузка {url}: {len(data)} из {expected} байт")
    with dest.open("wb") as f:
        f.write(data)


def _is_executable(path: Path) -> bool:
    return path.exists() and os.access(path, os.X_OK)


def _merge_tree(src: Path, dst: Path) -> None:
    """Рекурсивно сливает src в dst, не удаляя существующие файлы/папки."""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            _merge_tree(item, target)
        else:
            if target.exists():
                target.unlink()
            shutil.move(str(item), str(target))


def _extract_deb(deb_path: Path, dest: Path) -> None:
    """Распаковывает .deb пакет и сливает его дерево в dest."""
    import tempfile

    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        subprocess.run(["dpkg-deb", "-x", str(deb_path), str(tmp_path)], check=True)
        _merge_tree(tmp_path, dest)


def _find_libtesseract(base: Path) -> Path | None:
    for so in base.rglob("libtesseract.so*"):
        return so
    return None


def install_tesseract() -> None:
    """Скачивает tesseract .deb пакеты и языковые данные."""
    base = _ensure_dir(_base_dir())
    binary = _binary_path()
    tessdata = _ensure_dir(_tessdata_dir())

    if not _is_executable(binary):
        logger.info("Установка bundled Tesseract...")
        for pkg_name, url in PACKAGES.items():
            deb = base / f"{pkg_name}.deb"
            if not deb.exists():
                _download(url, deb)
            _extract_deb(deb, base)
            deb.unlink(missing_ok=True)

        # Делаем бинарник исполняемым
        if binary.exists():
            binary.chmod(binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # libtesseract может быть в usr/lib/x86_64-linux-gnu/ — добавим в LD_LIBRARY_PATH
        lib = _find_libtesseract(base)
        if lib:
            lib_dir = str(lib.parent)
            logger.info("Найдена libtesseract в %s", lib_dir)
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}{os.pathsep}{os.environ.get('LD_LIBRARY_PATH', '')}"

    # Языковые данные из Ubuntu .deb пакетов
    for lang in LANGS:
        traineddata = tessdata / f"{lang}.traineddata"
        if traineddata.exists():
            continue
        pkg_name = f"tesseract-ocr-{lang}"
        url = f"{UBUNTU_MIRROR}/pool/universe/t/tesseract-lang/{pkg_name}_4.1.0-2_all.deb"
        deb = base / f"{pkg_name}.deb"
        try:
            _download(url, deb)
            _extract_deb(deb, base)
            deb.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Не удалось установить язык %s: %s", lang, exc)


def get_tesseract_cmd() -> tuple[str, str] | None:
    """Возвращает (tesseract_cmd, tessdata_prefix) для bundled версии.

    Сначала проверяет системный tesseract. Если его нет — скачивает bundled.
    """
    system = shutil.which("tesseract")
    if system:
        return system, ""

    binary = _binary_path()
    if not _is_executable(binary):
        install_tesseract()

    if not _is_executable(binary):
        return None

    # Убедимся, что libtesseract найдётся
    lib = _find_libtesseract(_base_dir())
    if lib:
        lib_dir = str(lib.parent)
        current = os.environ.get("LD_LIBRARY_PATH", "")
        if lib_dir not in current.split(os.pathsep):
            os.environ["LD_LIBRARY_PATH"] = f"{lib_dir}{os.pathsep}{current}".strip(os.pathsep)

    tessdata = _tessdata_dir()
    return str(binary), str(tessdata)


def cleanup_bundled_tesseract() -> None:
    """Удаляет скачанные bundled файлы."""
    base = _base_dir()
    if base.exists():
        shutil.rmtree(base)
