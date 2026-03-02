from __future__ import annotations

import pathlib
import re
import sys
from collections import defaultdict

from sqlmodel import Session, SQLModel, create_engine, delete, select

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app.db import init_db, session
from backend.app.models import NewsItem, NewsPersonMention, Person


def build_mentions() -> int:
    """
    简单的共现抽取：
    - 针对每篇有 raw_text 的新闻
    - 查找同公司所有 Person 的姓名在正文中出现（子串匹配）
    - 写入 NewsPersonMention（每文每人最多一条，mention_count=出现次数）
    """
    init_db()
    total_inserted = 0
    with session() as s:
        people_by_company: dict[int, list[Person]] = defaultdict(list)
        for p in s.exec(select(Person)).all():
            if p.company_id is not None:
                people_by_company[p.company_id].append(p)

        # 清空旧数据（全量重建）
        s.exec(delete(NewsPersonMention))

        news_items = list(s.exec(select(NewsItem).where(NewsItem.raw_text.is_not(None))).all())
        for news in news_items:
            if not news.company_id or not news.raw_text:
                continue
            text = news.raw_text
            persons = people_by_company.get(news.company_id, [])
            for person in persons:
                if not person.name:
                    continue
                # 计数：粗略用正则全匹配
                pattern = re.escape(person.name)
                hits = re.findall(pattern, text)
                if not hits:
                    continue
                mention = NewsPersonMention(news_id=news.id, person_id=person.id, mention_count=len(hits))  # type: ignore[arg-type]
                s.add(mention)
                total_inserted += 1

        s.commit()
    return total_inserted


def main() -> None:
    inserted = build_mentions()
    print(f"rebuild mentions done, rows={inserted}")


if __name__ == "__main__":
    main()

