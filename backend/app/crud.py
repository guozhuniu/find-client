from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, col, func, select

from backend.app.models import Company, NewsItem, NewsPersonMention, OrgNode, OrgNodeType, Person, Relationship


def create_company(s: Session, company: Company) -> Company:
    s.add(company)
    s.commit()
    s.refresh(company)
    return company


def list_companies(s: Session, query: Optional[str] = None, limit: int = 50) -> list[Company]:
    stmt = select(Company).order_by(Company.id.desc()).limit(limit)
    if query:
        q = f"%{query.strip()}%"
        stmt = (
            select(Company)
            .where(col(Company.name).like(q) | col(Company.aliases).like(q))
            .order_by(Company.id.desc())
            .limit(limit)
        )
    return list(s.exec(stmt).all())


def get_company(s: Session, company_id: int) -> Optional[Company]:
    return s.get(Company, company_id)


def create_person(s: Session, person: Person) -> Person:
    s.add(person)
    s.commit()
    s.refresh(person)
    return person


def get_person(s: Session, person_id: int) -> Optional[Person]:
    return s.get(Person, person_id)


def list_people(s: Session, company_id: Optional[int] = None, query: Optional[str] = None, limit: int = 50) -> list[Person]:
    stmt = select(Person).order_by(Person.id.desc()).limit(limit)
    if company_id is not None:
        stmt = stmt.where(Person.company_id == company_id)
    if query:
        q = f"%{query.strip()}%"
        stmt = stmt.where(col(Person.name).like(q) | col(Person.title).like(q))
    return list(s.exec(stmt).all())


def create_org_node(s: Session, node: OrgNode) -> OrgNode:
    s.add(node)
    s.commit()
    s.refresh(node)
    return node


def get_org_node(s: Session, node_id: int) -> Optional[OrgNode]:
    return s.get(OrgNode, node_id)


def list_org_children(s: Session, company_id: int, parent_id: Optional[int]) -> list[OrgNode]:
    stmt = (
        select(OrgNode)
        .where(OrgNode.company_id == company_id)
        .where(OrgNode.parent_id == parent_id)
        .order_by(OrgNode.sort_order.asc(), OrgNode.id.asc())
    )
    return list(s.exec(stmt).all())


def org_node_has_children(s: Session, node_id: int) -> bool:
    stmt = select(func.count(OrgNode.id)).where(OrgNode.parent_id == node_id)
    return (s.exec(stmt).one() or 0) > 0


def upsert_news_item_by_url(s: Session, item: NewsItem) -> NewsItem:
    existing = s.exec(select(NewsItem).where(NewsItem.url == item.url)).first()
    if existing:
        existing.title = item.title or existing.title
        existing.publisher = item.publisher or existing.publisher
        existing.published_at = item.published_at or existing.published_at
        existing.summary = item.summary or existing.summary
        existing.raw_text = item.raw_text or existing.raw_text
        existing.company_id = item.company_id or existing.company_id
        existing.person_id = item.person_id or existing.person_id
        existing.relevance_score = item.relevance_score
        s.add(existing)
        s.commit()
        s.refresh(existing)
        return existing
    s.add(item)
    s.commit()
    s.refresh(item)
    return item


def list_news_for_person(s: Session, person_id: int, limit: int = 20) -> list[NewsItem]:
    stmt = (
        select(NewsItem)
        .where(NewsItem.person_id == person_id)
        .order_by(NewsItem.published_at.desc().nullslast(), NewsItem.id.desc())
        .limit(limit)
    )
    return list(s.exec(stmt).all())


def _build_parent_map(s: Session, company_id: int) -> dict[int, Optional[int]]:
    stmt = select(OrgNode.id, OrgNode.parent_id).where(OrgNode.company_id == company_id)
    return {row[0]: row[1] for row in s.exec(stmt).all()}


def _person_to_org_node(s: Session, company_id: int) -> dict[int, int]:
    stmt = (
        select(OrgNode.person_id, OrgNode.id)
        .where(OrgNode.company_id == company_id)
        .where(OrgNode.node_type == OrgNodeType.person)
        .where(OrgNode.person_id.is_not(None))
    )
    return {row[0]: row[1] for row in s.exec(stmt).all() if row[0] is not None}


def _path_to_root(node_id: int, parent_map: dict[int, Optional[int]], max_hops: int = 50) -> list[int]:
    path: list[int] = []
    cur: Optional[int] = node_id
    hops = 0
    while cur is not None and hops < max_hops:
        path.append(cur)
        cur = parent_map.get(cur)
        hops += 1
    return path


def _org_distance(a_node: int, b_node: int, parent_map: dict[int, Optional[int]]) -> Optional[int]:
    a_path = _path_to_root(a_node, parent_map)
    b_path = _path_to_root(b_node, parent_map)
    if not a_path or not b_path:
        return None
    a_index = {nid: i for i, nid in enumerate(a_path)}
    best: Optional[int] = None
    for j, nid in enumerate(b_path):
        if nid in a_index:
            dist = a_index[nid] + j
            best = dist if best is None else min(best, dist)
    return best


def recompute_relationships(
    s: Session,
    company_id: int,
    half_life_days: int = 180,
    max_pairs: int = 5000,
) -> int:
    """
    亲密指数：组织距离 + 新闻共现 + 新闻时间相近，均可解释。
    - 组织距离：同节点/同上级更强
    - 新闻共现：同一篇新闻里同时提到两人
    - 新闻时间相近：两人近 N 天都有新闻，且发布时间接近
    """
    people = list(s.exec(select(Person).where(Person.company_id == company_id)).all())
    if len(people) < 2:
        return 0

    parent_map = _build_parent_map(s, company_id)
    p2n = _person_to_org_node(s, company_id)

    now = datetime.utcnow()
    window = timedelta(days=half_life_days)

    # 预取每个人最近新闻时间戳（简化：只取最新一条）
    latest_news: dict[int, Optional[datetime]] = {}
    for p in people:
        item = s.exec(
            select(NewsItem.published_at)
            .where(NewsItem.person_id == p.id)
            .order_by(NewsItem.published_at.desc().nullslast(), NewsItem.id.desc())
            .limit(1)
        ).first()
        latest_news[p.id] = item

    # 预取新闻共现：从 NewsPersonMention 里统计同文共现次数
    mentions = list(
        s.exec(
            select(NewsPersonMention.news_id, NewsPersonMention.person_id, NewsPersonMention.mention_count)
        ).all()
    )
    news_to_people: dict[int, list[int]] = {}
    for news_id, person_id, _cnt in mentions:
        if person_id not in {p.id for p in people if p.id is not None}:
            continue
        news_to_people.setdefault(news_id, []).append(person_id)

    pair_common_news: dict[tuple[int, int], int] = {}
    for persons in news_to_people.values():
        unique_ids = sorted(set(persons))
        for i in range(len(unique_ids)):
            for j in range(i + 1, len(unique_ids)):
                key = (unique_ids[i], unique_ids[j])
                pair_common_news[key] = pair_common_news.get(key, 0) + 1

    count = 0
    created_or_updated = 0
    for i in range(len(people)):
        for j in range(i + 1, len(people)):
            if count >= max_pairs:
                return created_or_updated
            count += 1
            a = people[i]
            b = people[j]

            org_score = 0.0
            org_dist: Optional[int] = None
            if a.id in p2n and b.id in p2n:
                org_dist = _org_distance(p2n[a.id], p2n[b.id], parent_map)
                if org_dist is not None:
                    org_score = 1.0 / (1.0 + org_dist)  # dist=0 -> 1.0

            news_score = 0.0
            ta = latest_news.get(a.id)
            tb = latest_news.get(b.id)
            if ta and tb:
                if (now - ta) <= window and (now - tb) <= window:
                    delta_days = abs((ta - tb).days)
                    news_score = 1.0 / (1.0 + delta_days)  # 越近越强

            # 共现分：同一新闻里共现次数越多越强（上限 1.0）
            key = tuple(sorted((a.id, b.id)))  # type: ignore[arg-type]
            co_count = pair_common_news.get(key, 0)
            co_score = min(1.0, co_count / 3.0)  # 3 篇共现视为满分

            score = 100.0 * (0.7 * org_score + 0.2 * co_score + 0.1 * news_score)

            evidence = {
                "org_distance": org_dist,
                "org_score": org_score,
                "news_latest_a": ta.isoformat() if ta else None,
                "news_latest_b": tb.isoformat() if tb else None,
                "news_score": news_score,
                "common_news_count": co_count,
            }

            existing = s.exec(
                select(Relationship)
                .where(Relationship.company_id == company_id)
                .where(Relationship.person_a_id == a.id)
                .where(Relationship.person_b_id == b.id)
            ).first()

            if existing:
                existing.score = score
                existing.evidence = str(evidence)
                existing.updated_at = datetime.utcnow()
                s.add(existing)
            else:
                s.add(
                    Relationship(
                        company_id=company_id,
                        person_a_id=a.id,
                        person_b_id=b.id,
                        score=score,
                        evidence=str(evidence),
                    )
                )
            created_or_updated += 1

    s.commit()
    return created_or_updated

