"""Unit-тесты для any2md.tesseract_bundled.

TDD-цикл по tdd-guide. Целевые AC:
  AC-1: _get_expected_sha256 — env-override работает
  AC-2: _get_expected_sha256 — None если нет ни env, ни константы
  AC-3: _sha256_file — корректный хэш
  AC-4: _is_executable — True для исполняемого, False для отсутствующего
  AC-5: _merge_tree — сливает деревья без удаления существующих
  AC-6: _find_libtesseract — находит .so файл
  AC-7: _find_libtesseract — None если нет .so
  AC-8: _base_dir / _tessdata_dir / _binary_path — корректные пути
  AC-9: cleanup_bundled_tesseract — удаляет директорию
  AC-10: get_tesseract_cmd — системный tesseract имеет приоритет
  AC-11: _download_with_fallback — бросает RuntimeError если все URL недоступны
  AC-12: _download_with_fallback — проверяет SHA256
"""

import hashlib
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from any2md.tesseract_bundled import (
    LANGS,
    LEPTONICA_VERSION,
    PACKAGES,
    TESSERACT_VERSION,
    _base_dir,
    _binary_path,
    _download_with_fallback,
    _find_libtesseract,
    _get_expected_sha256,
    _is_executable,
    _merge_tree,
    _sha256_file,
    _tessdata_dir,
    cleanup_bundled_tesseract,
    get_tesseract_cmd,
)


# ---------------------------------------------------------------------------
# AC-1: _get_expected_sha256 — env-override работает
# ---------------------------------------------------------------------------

def test_get_expected_sha256_env_override(monkeypatch):
    """AC-1: env ANY2MD_SHA256_<PKG> перекрывает встроенную константу."""
    monkeypatch.setenv("ANY2MD_SHA256_LIBTESSERACT5", "abc123")
    result = _get_expected_sha256("libtesseract5")
    assert result == "abc123"


# ---------------------------------------------------------------------------
# AC-2: _get_expected_sha256 — None если нет ни env, ни константы
# ---------------------------------------------------------------------------

def test_get_expected_sha256_none_default(monkeypatch):
    """AC-2: _get_expected_sha256 возвращает None если SHA256 не задан."""
    monkeypatch.delenv("ANY2MD_SHA256_TESSERACT_OCR", raising=False)
    result = _get_expected_sha256("tesseract-ocr")
    assert result is None


# ---------------------------------------------------------------------------
# AC-3: _sha256_file — корректный хэш
# ---------------------------------------------------------------------------

def test_sha256_file(tmp_path):
    """AC-3: _sha256_file возвращает корректный SHA256 хэш."""
    src = tmp_path / "test.bin"
    data = b"hello world"
    src.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert _sha256_file(src) == expected


# ---------------------------------------------------------------------------
# AC-4: _is_executable — True для исполняемого, False для отсутствующего
# ---------------------------------------------------------------------------

def test_is_executable_true(tmp_path):
    """AC-4: _is_executable True для исполняемого файла."""
    src = tmp_path / "script.sh"
    src.write_text("#!/bin/bash\necho hello")
    src.chmod(src.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    assert _is_executable(src) is True


def test_is_executable_false_nonexistent(tmp_path):
    """AC-4b: _is_executable False для несуществующего файла."""
    assert _is_executable(tmp_path / "nonexistent") is False


def test_is_executable_false_no_exec_bit(tmp_path):
    """AC-4c: _is_executable False для файла без execute-бита."""
    src = tmp_path / "file.txt"
    src.write_text("hello")
    src.chmod(0o644)  # rw-r--r-- — нет execute
    assert _is_executable(src) is False


# ---------------------------------------------------------------------------
# AC-5: _merge_tree — сливает деревья без удаления существующих
# ---------------------------------------------------------------------------

def test_merge_tree(tmp_path):
    """AC-5: _merge_tree сливает исходное дерево в целевое."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    # Создаём структуру в src
    (src / "dir1").mkdir(parents=True)
    (src / "dir1" / "file1.txt").write_text("content1")
    (src / "file2.txt").write_text("content2")

    # В dst уже есть dir1
    (dst / "dir1").mkdir(parents=True)
    (dst / "dir1" / "existing.txt").write_text("old")

    _merge_tree(src, dst)

    assert (dst / "dir1" / "file1.txt").read_text() == "content1"
    assert (dst / "dir1" / "existing.txt").read_text() == "old"  # не удалён
    assert (dst / "file2.txt").read_text() == "content2"


# ---------------------------------------------------------------------------
# AC-6: _find_libtesseract — находит .so файл
# ---------------------------------------------------------------------------

def test_find_libtesseract_finds_so(tmp_path):
    """AC-6: _find_libtesseract находит libtesseract.so."""
    base = tmp_path / "base"
    lib_dir = base / "usr" / "lib" / "x86_64-linux-gnu"
    lib_dir.mkdir(parents=True)
    so_file = lib_dir / "libtesseract.so.5"
    so_file.write_text("fake lib")

    result = _find_libtesseract(base)
    assert result is not None
    assert result.name == "libtesseract.so.5"


# ---------------------------------------------------------------------------
# AC-7: _find_libtesseract — None если нет .so
# ---------------------------------------------------------------------------

def test_find_libtesseract_none(tmp_path):
    """AC-7: _find_libtesseract возвращает None если нет .so."""
    base = tmp_path / "empty"
    base.mkdir()
    result = _find_libtesseract(base)
    assert result is None


# ---------------------------------------------------------------------------
# AC-8: пути _base_dir / _tessdata_dir / _binary_path
# ---------------------------------------------------------------------------

def test_base_dir_contains_any2md():
    """AC-8: _base_dir содержит .any2md/tesseract в пути."""
    result = _base_dir()
    assert ".any2md" in str(result)
    assert "tesseract" in str(result)


def test_binary_path_under_base():
    """AC-8b: _binary_path указывает на usr/bin/tesseract."""
    result = _binary_path()
    assert "usr" in str(result)
    assert "bin" in str(result)
    assert "tesseract" in str(result)


# ---------------------------------------------------------------------------
# AC-9: cleanup_bundled_tesseract — удаляет директорию
# ---------------------------------------------------------------------------

def test_cleanup_removes_directory(tmp_path, monkeypatch):
    """AC-9: cleanup_bundled_tesseract удаляет папку .any2md/tesseract."""
    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_base.mkdir(parents=True)
    (fake_base / "some_file").write_text("data")

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    cleanup_bundled_tesseract()

    assert not fake_base.exists()


def test_cleanup_noop_if_not_exists(tmp_path, monkeypatch):
    """AC-9b: cleanup_bundled_tesseract не падает если папки нет."""
    monkeypatch.setattr(
        "any2md.tesseract_bundled._base_dir",
        lambda: tmp_path / ".any2md" / "nonexistent",
    )
    # Не должно бросать
    cleanup_bundled_tesseract()


# ---------------------------------------------------------------------------
# AC-10: get_tesseract_cmd — системный tesseract имеет приоритет
# ---------------------------------------------------------------------------

def test_get_tesseract_cmd_system_priority(monkeypatch):
    """AC-10: если системный tesseract есть, bundled не используется."""
    monkeypatch.setattr("any2md.tesseract_bundled.shutil.which", lambda _: "/usr/bin/tesseract")
    cmd, prefix = get_tesseract_cmd()
    assert cmd == "/usr/bin/tesseract"
    assert prefix == ""


def test_get_tesseract_cmd_returns_none_if_no_binary(monkeypatch, tmp_path):
    """AC-10b: get_tesseract_cmd возвращает None если бинарник не появился."""
    monkeypatch.setattr("any2md.tesseract_bundled.shutil.which", lambda _: None)
    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: tmp_path / "fake_base")
    monkeypatch.setattr(
        "any2md.tesseract_bundled._binary_path",
        lambda: tmp_path / "fake_base" / "usr" / "bin" / "tesseract",
    )
    # install_tesseract не должна сработать без сети — патчим
    monkeypatch.setattr(
        "any2md.tesseract_bundled.install_tesseract",
        lambda: None,
    )
    result = get_tesseract_cmd()
    assert result is None


# ---------------------------------------------------------------------------
# AC-11: _download_with_fallback — бросает RuntimeError если все URL недоступны
# ---------------------------------------------------------------------------

def test_download_with_fallback_raises_on_all_failures(tmp_path):
    """AC-11: _download_with_fallback бросает RuntimeError если все URL недоступны."""
    dest = tmp_path / "output.deb"

    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        with pytest.raises(RuntimeError, match="Не удалось скачать"):
            _download_with_fallback(["http://fake1/test.deb", "http://fake2/test.deb"], dest)


# ---------------------------------------------------------------------------
# AC-12: _download_with_fallback — проверяет SHA256
# ---------------------------------------------------------------------------

def test_download_with_fallback_sha256_mismatch(tmp_path):
    """AC-12: _download_with_fallback бросает RuntimeError при несовпадении SHA256.

    Функция ловит внутреннюю SHA256-ошибку и оборачивает в RuntimeError
    «Не удалось скачать», поэтому проверяем внешнее сообщение.
    """
    dest = tmp_path / "output.deb"
    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": "11"}
    fake_response.read = MagicMock(side_effect=[b"hello world", b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises(RuntimeError, match="Не удалось скачать"):
            _download_with_fallback(
                ["http://fake/test.deb"],
                dest,
                expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
            )
    # Файл должен быть удалён при ошибке
    assert not dest.exists()


def test_download_with_fallback_sha256_match(tmp_path):
    """AC-12b: _download_with_fallback проходит при совпадении SHA256."""
    dest = tmp_path / "output.deb"
    data = b"hello world"
    correct_sha = hashlib.sha256(data).hexdigest()

    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": str(len(data))}
    fake_response.read = MagicMock(side_effect=[data, b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_response):
        _download_with_fallback(
            ["http://fake/test.deb"],
            dest,
            expected_sha256=correct_sha,
        )

    assert dest.read_bytes() == data


# ---------------------------------------------------------------------------
# Константы версий (AC-extra: проверка что константы определены)
# ---------------------------------------------------------------------------

def test_version_constants_defined():
    """Константы версий определены и непусты."""
    assert TESSERACT_VERSION
    assert LEPTONICA_VERSION
    assert len(LANGS) == 5
    assert "eng" in LANGS
    assert "rus" in LANGS
    assert "libtesseract5" in PACKAGES
    assert "tesseract-ocr" in PACKAGES
    assert "liblept5" in PACKAGES


# ---------------------------------------------------------------------------
# AC-13: _download_with_fallback — неполная загрузка (line 103)
# ---------------------------------------------------------------------------

def test_download_partial_download_raises(tmp_path):
    """AC-13: Content-Length не совпадает с фактическим размером → RuntimeError."""
    from any2md.tesseract_bundled import _download_with_fallback

    dest = tmp_path / "partial.deb"
    # Content-Length = 20, но реально скачали только 5 байт
    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": "20"}
    fake_response.read = MagicMock(side_effect=[b"hello", b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises(RuntimeError, match="Не удалось скачать"):
            _download_with_fallback(
                ["http://fake/test.deb"],
                dest,
                expected_sha256=None,
            )
    # Файл удалён после ошибки
    assert not dest.exists()


# ---------------------------------------------------------------------------
# AC-14: _download — URL construction с fallback mirror (lines 128-129)
# ---------------------------------------------------------------------------

def test_download_constructs_fallback_urls(tmp_path):
    """AC-14: _download конструирует fallback URLs когда mirror не совпадает."""
    from any2md.tesseract_bundled import _download

    dest = tmp_path / "test.deb"
    data = b"test data"
    correct_sha = hashlib.sha256(data).hexdigest()

    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": str(len(data))}
    fake_response.read = MagicMock(side_effect=[data, b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    # URL указывает на другой mirror — _download должен построить fallback
    url = "http://other-mirror.com/pool/test.deb"
    with patch("urllib.request.urlopen", return_value=fake_response) as mock_urlopen:
        _download(url, dest, expected_sha256=correct_sha)

    assert dest.read_bytes() == data
    # Должен был попробовать хотя бы один URL
    assert mock_urlopen.call_count >= 1


# ---------------------------------------------------------------------------
# AC-15: _merge_tree — перезапись существующего файла (line 147)
# ---------------------------------------------------------------------------

def test_merge_tree_overwrites_existing(tmp_path):
    """AC-15: _merge_tree перезаписывает существующие файлы в dst."""
    from any2md.tesseract_bundled import _merge_tree

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    # В src и dst один и тот же файл с разным содержимым
    (src / "conflict.txt").write_text("new content")
    (dst / "conflict.txt").write_text("old content")

    _merge_tree(src, dst)
    assert (dst / "conflict.txt").read_text() == "new content"


# ---------------------------------------------------------------------------
# AC-16: _merge_tree — рекурсивное слияние поддиректорий
# ---------------------------------------------------------------------------

def test_merge_tree_recursive_dirs(tmp_path):
    """AC-16: _merge_tree рекурсивно сливает поддиректории."""
    from any2md.tesseract_bundled import _merge_tree

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    (src / "a" / "b").mkdir(parents=True)
    (src / "a" / "b" / "deep.txt").write_text("deep")
    (src / "top.txt").write_text("top")
    dst.mkdir()

    _merge_tree(src, dst)
    assert (dst / "top.txt").read_text() == "top"
    assert (dst / "a" / "b" / "deep.txt").read_text() == "deep"


# ---------------------------------------------------------------------------
# AC-17: _extract_deb — вызов dpkg-deb (line 159)
# ---------------------------------------------------------------------------

def test_extract_deb_calls_dpkg_deb(tmp_path):
    """AC-17: _extract_deb вызывает dpkg-deb -x и сливает дерево."""
    from any2md.tesseract_bundled import _extract_deb

    deb_path = tmp_path / "fake.deb"
    deb_path.write_bytes(b"fake deb")
    dest = tmp_path / "dest"

    def fake_run(cmd, check=True):
        # Имитируем dpkg-deb: создаём файлы в tmp_path
        # cmd[-1] — это tmp_path куда распаковать
        extract_to = Path(cmd[-1])
        (extract_to / "usr" / "bin").mkdir(parents=True)
        (extract_to / "usr" / "bin" / "tesseract").write_text("#!/bin/bash\necho ok")

    with patch("subprocess.run", side_effect=fake_run):
        _extract_deb(deb_path, dest)

    assert (dest / "usr" / "bin" / "tesseract").exists()


# ---------------------------------------------------------------------------
# AC-18: install_tesseract — early return если бинарник есть (line 175)
# ---------------------------------------------------------------------------

def test_install_tesseract_early_return(tmp_path, monkeypatch):
    """AC-18: install_tesseract сразу возвращает если бинарник уже исполняемый."""
    from any2md.tesseract_bundled import install_tesseract

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o755)

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr(
        "any2md.tesseract_bundled._tessdata_dir",
        lambda: fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata",
    )

    # Не должно вызываться скачивание
    with patch("any2md.tesseract_bundled._download") as mock_dl:
        install_tesseract()
        mock_dl.assert_not_called()


# ---------------------------------------------------------------------------
# AC-19: install_tesseract — основное тело (lines 183-209)
# ---------------------------------------------------------------------------

def test_install_tesseract_downloads_and_sets_permissions(tmp_path, monkeypatch):
    """AC-19: install_tesseract скачивает пакеты, распаковывает, ставит права."""
    from any2md.tesseract_bundled import install_tesseract

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_base.mkdir(parents=True)
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    # Бинарник создан, но НЕ исполняемый
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o644)

    tessdata = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    tessdata.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr("any2md.tesseract_bundled._tessdata_dir", lambda: tessdata)

    with patch("any2md.tesseract_bundled._download"), \
         patch("any2md.tesseract_bundled._extract_deb"):
        install_tesseract()

    # Проверяем что права выставлены
    import stat
    mode = fake_binary.stat().st_mode
    assert mode & stat.S_IXUSR  # owner execute


def test_install_tesseract_skips_existing_traineddata(tmp_path, monkeypatch):
    """AC-19b: install_tesseract не скачивает язык если traineddata уже есть."""
    from any2md.tesseract_bundled import install_tesseract

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o644)

    tessdata = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    tessdata.mkdir(parents=True)
    # Все языковые файлы уже на месте
    for lang in ("eng", "rus", "fra", "deu", "spa"):
        (tessdata / f"{lang}.traineddata").write_text("fake")

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr("any2md.tesseract_bundled._tessdata_dir", lambda: tessdata)

    downloaded_pkgs = []
    def tracking_download(*args, **kwargs):
        downloaded_pkgs.append(args[0])

    with patch("any2md.tesseract_bundled._download", side_effect=tracking_download), \
         patch("any2md.tesseract_bundled._extract_deb"):
        install_tesseract()

    # Основные пакеты скачаны (3 штуки), но языковые — нет
    lang_downloads = [u for u in downloaded_pkgs if "tesseract-ocr-" in u and "tesseract-lang" in u]
    assert len(lang_downloads) == 0, f"Языковые пакеты не должны скачиваться: {lang_downloads}"


def test_install_tesseract_lang_download_error_suppressed(tmp_path, monkeypatch):
    """AC-19c: ошибка скачивания языка не прерывает установку.

    _download вызывается дважды: для основных пакетов (без ошибки)
    и для языковых пакетов (с ошибкой). Ошибка языка подавляется.
    """
    from any2md.tesseract_bundled import install_tesseract

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o644)

    tessdata = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    tessdata.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr("any2md.tesseract_bundled._tessdata_dir", lambda: tessdata)

    def selective_download(url, *args, **kwargs):
        # Основные пакеты — OK, языковые — ошибка
        if "tesseract-lang" in url:
            raise RuntimeError("Network error")

    with patch("any2md.tesseract_bundled._download", side_effect=selective_download), \
         patch("any2md.tesseract_bundled._extract_deb"):
        # Не должно бросать — ошибка языка подавляется
        install_tesseract()


# ---------------------------------------------------------------------------
# AC-20: _tessdata_dir — поиск версии tessdata (lines 59-64)
# ---------------------------------------------------------------------------

def test_tessdata_dir_finds_version5(tmp_path, monkeypatch):
    """AC-20a: _tessdata_dir находит директорию с версией '5'."""
    from any2md.tesseract_bundled import _tessdata_dir

    fake_base = tmp_path / "base"
    v5 = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    v5.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    assert _tessdata_dir() == v5


def test_tessdata_dir_finds_version4(tmp_path, monkeypatch):
    """AC-20b: _tessdata_dir находит директорию с версией '4.00'."""
    from any2md.tesseract_bundled import _tessdata_dir

    fake_base = tmp_path / "base"
    v4 = fake_base / "usr" / "share" / "tesseract-ocr" / "4.00" / "tessdata"
    v4.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    assert _tessdata_dir() == v4


def test_tessdata_dir_fallback(tmp_path, monkeypatch):
    """AC-20c: _tessdata_dir возвращает путь по умолчанию если версий нет."""
    from any2md.tesseract_bundled import _tessdata_dir

    fake_base = tmp_path / "base"
    fake_base.mkdir()

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    result = _tessdata_dir()
    assert "5" in str(result)  # fallback на версию 5


# ---------------------------------------------------------------------------
# AC-21: _download — URL совпадает с mirror (line 125)
# ---------------------------------------------------------------------------

def test_download_url_matches_mirror(tmp_path):
    """AC-21: _download когда URL уже начинается с mirror."""
    from any2md.tesseract_bundled import _download

    dest = tmp_path / "test.deb"
    data = b"mirror match"
    correct_sha = hashlib.sha256(data).hexdigest()

    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": str(len(data))}
    fake_response.read = MagicMock(side_effect=[data, b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    # URL совпадает с default mirror
    url = "http://archive.ubuntu.com/ubuntu/pool/test.deb"
    with patch("urllib.request.urlopen", return_value=fake_response):
        _download(url, dest, expected_sha256=correct_sha)

    assert dest.read_bytes() == data


# ---------------------------------------------------------------------------
# AC-22: install_tesseract — libtesseract найден (lines 192-194)
# ---------------------------------------------------------------------------

def test_install_tesseract_finds_libtesseract(tmp_path, monkeypatch):
    """AC-22: install_tesseract находит libtesseract.so и добавляет в LD_LIBRARY_PATH."""
    from any2md.tesseract_bundled import install_tesseract

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o644)

    # Создаём libtesseract.so
    lib_dir = fake_base / "usr" / "lib" / "x86_64-linux-gnu"
    lib_dir.mkdir(parents=True)
    (lib_dir / "libtesseract.so.5").write_text("fake lib")

    tessdata = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    tessdata.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr("any2md.tesseract_bundled._tessdata_dir", lambda: tessdata)

    old_ld = os.environ.get("LD_LIBRARY_PATH", "")
    with patch("any2md.tesseract_bundled._download"), \
         patch("any2md.tesseract_bundled._extract_deb"):
        install_tesseract()

    # LD_LIBRARY_PATH должен содержать путь к libtesseract
    new_ld = os.environ.get("LD_LIBRARY_PATH", "")
    assert str(lib_dir) in new_ld


# ---------------------------------------------------------------------------
# AC-23: get_tesseract_cmd — bundled путь с lib (lines 229-237)
# ---------------------------------------------------------------------------

def test_get_tesseract_cmd_bundled_with_lib(tmp_path, monkeypatch):
    """AC-23: get_tesseract_cmd для bundled tesseract с libtesseract.so."""
    from any2md.tesseract_bundled import get_tesseract_cmd

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o755)

    # libtesseract.so
    lib_dir = fake_base / "usr" / "lib" / "x86_64-linux-gnu"
    lib_dir.mkdir(parents=True)
    (lib_dir / "libtesseract.so.5").write_text("fake lib")

    tessdata = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    tessdata.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled.shutil.which", lambda _: None)
    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr("any2md.tesseract_bundled._tessdata_dir", lambda: tessdata)

    cmd, prefix = get_tesseract_cmd()
    assert cmd == str(fake_binary)
    assert prefix == str(tessdata)


# ---------------------------------------------------------------------------
# AC-24: _download — fallback URL construction (line 129)
# ---------------------------------------------------------------------------

def test_download_fallback_url_construction(tmp_path):
    """AC-24: _download конструирует fallback URL когда mirror не совпадает с URL."""
    from any2md.tesseract_bundled import _download

    dest = tmp_path / "test.deb"
    data = b"fallback"
    correct_sha = hashlib.sha256(data).hexdigest()

    fake_response = MagicMock()
    fake_response.headers = {"Content-Length": str(len(data))}
    fake_response.read = MagicMock(side_effect=[data, b""])
    fake_response.__enter__ = MagicMock(return_value=fake_response)
    fake_response.__exit__ = MagicMock(return_value=False)

    # URL на другом mirror — _download должен построить fallback
    url = "http://custom.mirror.com/pool/test.deb"
    with patch("urllib.request.urlopen", return_value=fake_response):
        _download(url, dest, expected_sha256=correct_sha)

    assert dest.read_bytes() == data


# ---------------------------------------------------------------------------
# AC-25: get_tesseract_cmd — bundled без libtesseract (line 226 path)
# ---------------------------------------------------------------------------

def test_get_tesseract_cmd_bundled_no_lib(tmp_path, monkeypatch):
    """AC-23b: get_tesseract_cmd для bundled без libtesseract.so."""
    from any2md.tesseract_bundled import get_tesseract_cmd

    fake_base = tmp_path / ".any2md" / "tesseract"
    fake_binary = fake_base / "usr" / "bin" / "tesseract"
    fake_binary.parent.mkdir(parents=True)
    fake_binary.write_text("#!/bin/bash\necho ok")
    fake_binary.chmod(0o755)

    tessdata = fake_base / "usr" / "share" / "tesseract-ocr" / "5" / "tessdata"
    tessdata.mkdir(parents=True)

    monkeypatch.setattr("any2md.tesseract_bundled.shutil.which", lambda _: None)
    monkeypatch.setattr("any2md.tesseract_bundled._base_dir", lambda: fake_base)
    monkeypatch.setattr("any2md.tesseract_bundled._binary_path", lambda: fake_binary)
    monkeypatch.setattr("any2md.tesseract_bundled._tessdata_dir", lambda: tessdata)

    cmd, prefix = get_tesseract_cmd()
    assert cmd == str(fake_binary)
    # Без libtesseract — LD_LIBRARY_PATH не меняется