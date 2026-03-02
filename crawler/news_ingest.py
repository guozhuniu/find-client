from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Optional

import httpx

from crawler.extract import extract_main_text
from crawler.gdelt_client import search_gdelt_docs


def _build_query(person: str, company: Optional[str]) -> str:
    person = person.strip()
    if company and company.strip():
        return f'"{person}" AND "{company.strip()}"'
    return f'"{person}"'


def _safe_dt_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def ingest(
    api_base: str,
    person_id: Optional[int],
    company_id: Optional[int],
    person: str,
    company: Optional[str],
    days: int,
    max_records: int,
) -> int:
    query = _build_query(person, company)
    articles = search_gdelt_docs(query=query, days=days, max_records=max_records)

    imported = 0
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for a in articles:
            extracted = extract_main_text(a.url)
            summary = None
            raw_text = None
            title = a.title
            if extracted:
                raw_text = extracted.text
                if extracted.title and len(extracted.title.strip()) >= 4:
                    title = extracted.title.strip()
                summary = (raw_text[:280] + "…") if len(raw_text) > 280 else raw_text

            payload = {
                "company_id": company_id,
                "person_id": person_id,
                "title": title,
                "url": a.url,
                "publisher": a.domain,
                "published_at": _safe_dt_iso(a.seendate),
                "summary": summary,
                "raw_text": raw_text,
                "relevance_score": 0.6,
            }

            r = client.post(f"{api_base.rstrip('/')}/api/news/import", json=payload)
            r.raise_for_status()
            imported += 1
    return imported


def main():
    ap = argparse.ArgumentParser(description="拉取人员相关新闻并入库（GDELT + 正文抽取骨架）")
    ap.add_argument("--api", required=True, help="后端 API Base，如 http://127.0.0.1:8000")
    ap.add_argument("--person", required=True, help="人员姓名（用于搜索召回）")
    ap.add_argument("--company", default=None, help="公司名（用于消歧/召回）")
    ap.add_argument("--person-id", type=int, default=None, help="写入到哪个 person_id（可选）")
    ap.add_argument("--company-id", type=int, default=None, help="写入到哪个 company_id（可选）")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--max", type=int, default=20)
    args = ap.parse_args()

    imported = ingest(
        api_base=args.api,
        person_id=args.person_id,
        company_id=args.company_id,
        person=args.person,
        company=args.company,
        days=args.days,
        max_records=args.max,
    )
    print(f"imported={imported}")


if __name__ == "__main__":
    main()

