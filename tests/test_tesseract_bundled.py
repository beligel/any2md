"""Unit-тесты для tesseract_bundled.py."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from any2md import tesseract_bundled as tb


def test_get_expected_sha256_from_env():
    pkg = "libtesseract5"
    env_key = "ANY2MD_SHA256_LIBTESSERACT5"
    with patch.dict(os.environ, {env_key: "abcd"}):
        assert tb._get_expected_sha256(pkg) == "abcd"


def test_get_expected_sha256_fallback():
    tb.PACKAGES["libtesseract5"]["sha256"] = "fallback"
    with patch.dict(os.environ, {}, clear=False):
        if "ANY2MD_SHA256_LIBTESSERACT5" in os.environ:
            del os.environ["ANY2MD_SHA256_LIBTESSERACT5"]
        assert tb._get_expected_sha256("libtesseract5") == "fallback"
    tb.PACKAGES["libtesseract5"]["sha256"] = None


def test_download_with_fallback_success(monkeypatch, tmp_path):
    dest = tmp_path / "test.deb"
    called = []

    class FakeResponse:
        headers = {"Content-Length": "5"}

        def read(self, size=-1):
            if not called:
                called.append(1)
                return b"hello"
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, timeout=None):
        return FakeResponse()

    monkeypatch.setattr(tb.urllib.request, "urlopen", fake_urlopen)
    tb._download_with_fallback(["http://a/test.deb"], dest)
    assert dest.read_bytes() == b"hello"


def test_download_with_fallback_sha256_mismatch(monkeypatch, tmp_path):
    dest = tmp_path / "test.deb"

    class FakeResponse:
        headers = {}

        def read(self, size=-1):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(tb.urllib.request, "urlopen", lambda req, timeout=None: FakeResponse())
    with pytest.raises(RuntimeError, match="URL"):
        tb._download_with_fallback(["http://a/x.deb"], dest, expected_sha256="wrong")


def test_get_tesseract_cmd_prefers_system():
    with patch.object(tb.shutil, "which", return_value="/usr/bin/tesseract"):
        assert tb.get_tesseract_cmd() == ("/usr/bin/tesseract", "")
