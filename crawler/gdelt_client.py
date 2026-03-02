from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx


@dataclass
class GdeltArticle:
    title: str
    url: str
    domain: Optional[str]
    source_country: Optional[str]
    language: Optional[str]
    seendate: Optional[datetime]


def _parse_seendate(v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    # 形如：20250101123000
    try:
        dt = datetime.strptime(v, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def search_gdelt_docs(
    query: str,
    days: int = 30,
    max_records: int = 20,
    *,
    timeout_s: float = 20.0,
) -> list[GdeltArticle]:
    """
    使用 GDELT 2.1 DOC API 做新闻候选召回（不含正文）。
    参考：GDELT 2.1 DOC API
    """
    max_records = max(1, min(max_records, 250))
    days = max(1, min(days, 3650))

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=days)

    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "startdatetime": start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end.strftime("%Y%m%d%H%M%S"),
        "sort": "HybridRel",
    }

    url = "https://api.gdeltproject.org/api/v2/doc/doc"
    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data: dict[str, Any] = r.json()

    articles: list[GdeltArticle] = []
    for a in data.get("articles", []) or []:
        articles.append(
            GdeltArticle(
                title=a.get("title") or "",
                url=a.get("url") or "",
                domain=a.get("domain"),
                source_country=a.get("sourceCountry"),
                language=a.get("language"),
                seendate=_parse_seendate(a.get("seendate")),
            )
        )
    return [x for x in articles if x.url and x.title]

