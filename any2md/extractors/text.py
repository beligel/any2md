"""Экстракторы для текстовых форматов и офисных документов."""

import html
from pathlib import Path

from ..core import maybe_decode
from .registry import ExtractionContext, register_extractor


def _fallback_text(path: Path, ctx: ExtractionContext) -> str:
    return f"```\n{maybe_decode(path, ctx.encoding)}\n```"


@register_extractor(".txt")
@register_extractor("text/plain")
def extract_txt(path: Path, ctx: ExtractionContext) -> str:
    return maybe_decode(path, ctx.encoding)


@register_extractor(".md")
def extract_md(path: Path, ctx: ExtractionContext) -> str:
    return maybe_decode(path, ctx.encoding)


@register_extractor(".html")
@register_extractor(".htm")
@register_extractor("text/html")
def extract_html(path: Path, ctx: ExtractionContext) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return _fallback_text(path, ctx)
    text = maybe_decode(path, ctx.encoding)
    soup = BeautifulSoup(text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    body = soup.get_text("\n", strip=True)
    out = []
    if title:
        out.append(f"# {html.escape(title)}")
    out.append(body)
    return "\n\n".join(out)


@register_extractor(".csv")
@register_extractor("text/csv")
def extract_csv(path: Path, ctx: ExtractionContext) -> str:
    import csv

    rows = []
    with open(path, "r", encoding=ctx.encoding, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append("| " + " | ".join(row) + " |")
    if not rows:
        return ""
    header_sep = "|" + "|".join([" --- " for _ in rows[0].split("|") if _]) + "|"
    return "\n".join([rows[0], header_sep] + rows[1:])


@register_extractor(".json")
@register_extractor("application/json")
def extract_json(path: Path, ctx: ExtractionContext) -> str:
    import json

    text = maybe_decode(path, ctx.encoding)
    data = json.loads(text)
    return f"```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"


@register_extractor(".xml")
@register_extractor("application/xml")
@register_extractor("text/xml")
def extract_xml(path: Path, ctx: ExtractionContext) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return _fallback_text(path, ctx)
    text = maybe_decode(path, ctx.encoding)
    soup = BeautifulSoup(text, "xml")
    return soup.get_text("\n", strip=True)
