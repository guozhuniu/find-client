from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import trafilatura


@dataclass
class ExtractedArticle:
    text: str
    title: Optional[str] = None


def extract_main_text(url: str, *, timeout_s: float = 20.0) -> Optional[ExtractedArticle]:
    """
    抽取网页正文（尽量通用）。失败时返回 None。
    """
    downloaded = trafilatura.fetch_url(url, timeout=timeout_s)
    if not downloaded:
        return None
    text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    if not text:
        return None
    meta = trafilatura.extract_metadata(downloaded)
    title = meta.title if meta else None
    return ExtractedArticle(text=text, title=title)

