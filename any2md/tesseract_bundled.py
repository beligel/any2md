"""Загрузка и настройка bundled Tesseract OCR.

Системный tesseract-ocr больше не требуется. При первом вызове OCR
any2md скачивает готовые Debian/Ubuntu .deb пакеты и распаковывает
их в папку проекта `.any2md/tesseract/`, если их ещё нет.
"""

import hashlib
import logging
import os
import shutil
import stat
import subprocess
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

# Ubuntu 24.04 (noble) amd64 .deb пакеты — стабильные URL.
# Можно заменить на ближайший mirror через переменную окружения ANY2MD_UBUNTU_MIRROR.
UBUNTU_MIRROR = os.environ.get("ANY2MD_UBUNTU_MIRROR", "http://archive.ubuntu.com/ubuntu")

# Версии пакетов вынесены в константы для удобства обновления.
TESSERACT_VERSION = "5.3.4-1build5"
LEPTONICA_VERSION = "1.82.0-3build4"
LANG_PACK_VERSION = "4.1.0-2"

PACKAGES = {
    "libtesseract5": {
        "url": f"{UBUNTU_MIRROR}/pool/universe/t/tesseract/libtesseract5_{TESSERACT_VERSION}_amd64.deb",
        "sha256": None,  # пользователь может задать через env ANY2MD_SHA256_<pkg>
    },
    "tesseract-ocr": {
        "url": f"{UBUNTU_MIRROR}/pool/universe/t/tesseract/tesseract-ocr_{TESSERACT_VERSION}_amd64.deb",
        "sha256": None,
    },
    "liblept5": {
        "url": f"{UBUNTU_MIRROR}/pool/universe/l/leptonlib/liblept5_{LEPTONICA_VERSION}_amd64.deb",
        "sha256": None,
    },
}


def _get_expected_sha256(pkg_name: str) -> str | None:
    """SHA256 для пакета: сначала env, потом встроенная константа."""
    env_key = f"ANY2MD_SHA256_{pkg_name.upper().replace('-', '_')}"
    return os.environ.get(env_key) or PACKAGES[pkg_name].get("sha256")


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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_with_fallback(urls: list[str], dest: Path, expected_sha256: str | None = None, chunk_size: int = 65536) -> None:
    """Скачивает файл с fallback URL и опциональной проверкой SHA256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None

    for url in urls:
        logger.info("Скачивание %s -> %s", url, dest)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "any2md/0.2.1"})
            with urllib.request.urlopen(req, timeout=120) as response:
                expected = response.headers.get("Content-Length")
                with dest.open("wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)

            if expected and int(expected) != dest.stat().st_size:
                raise RuntimeError(f"Неполная загрузка {url}: {dest.stat().st_size} из {expected} байт")

            if expected_sha256 and _sha256_file(dest) != expected_sha256:
                raise RuntimeError(f"SHA256 не совпадает для {url}")

            return
        except Exception as exc:
            last_error = exc
            logger.warning("Не удалось скачать %s: %s", url, exc)
            if dest.exists():
                dest.unlink(missing_ok=True)

    raise RuntimeError(f"Не удалось скачать ни с одного из URL: {urls}") from last_error


def _download(url: str, dest: Path, expected_sha256: str | None = None, chunk_size: int = 65536) -> None:
    """Скачивает файл по URL с fallback на зеркала."""
    mirrors = [os.environ.get("ANY2MD_UBUNTU_MIRROR", "").rstrip("/"), "http://archive.ubuntu.com/ubuntu"]
    mirrors = [m for m in mirrors if m]
    urls = []
    for mirror in dict.fromkeys(mirrors):  # сохраняем порядок, убираем дубликаты
        if url.startswith(mirror):
            urls.append(url)
        else:
            # Заменяем базовый mirror в URL на fallback
            rest = url.replace(UBUNTU_MIRROR, "").lstrip("/")
            urls.append(f"{mirror}/{rest}")
    urls = list(dict.fromkeys(urls))
    _download_with_fallback(urls, dest, expected_sha256=expected_sha256, chunk_size=chunk_size)


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

    if _is_executable(binary):
        return

    logger.info("Установка bundled Tesseract...")
    for pkg_name, meta in PACKAGES.items():
        deb = base / f"{pkg_name}.deb"
        if not deb.exists():
            _download(meta["url"], deb, expected_sha256=_get_expected_sha256(pkg_name))
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
        url = f"{UBUNTU_MIRROR}/pool/universe/t/tesseract-lang/{pkg_name}_{LANG_PACK_VERSION}_all.deb"
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
