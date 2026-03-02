from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from sqlmodel import select

from backend.app import crud
from backend.app.db import init_db, session
from backend.app.models import Company, NewsItem, OrgNode, Person, Relationship
from backend.app.schemas import (
    CompanyCreate,
    CompanyRead,
    NewsItemCreate,
    NewsItemRead,
    OrgNodeCreate,
    OrgNodeRead,
    PersonCreate,
    PersonRead,
    RecomputeRelationshipsRequest,
    RelationshipRead,
)
from backend.app.ui import router as ui_router


app = FastAPI(title="Find Client", version="0.1.0")
app.include_router(ui_router)


@app.on_event("startup")
def _startup() -> None:
    os.makedirs("backend/data", exist_ok=True)
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/companies", response_model=CompanyRead)
def api_create_company(payload: CompanyCreate):
    with session() as s:
        obj = Company(**payload.model_dump())
        obj = crud.create_company(s, obj)
        return obj


@app.get("/api/companies", response_model=list[CompanyRead])
def api_list_companies(q: Optional[str] = None, limit: int = Query(default=50, ge=1, le=500)):
    with session() as s:
        return crud.list_companies(s, query=q, limit=limit)


@app.get("/api/companies/{company_id}", response_model=CompanyRead)
def api_get_company(company_id: int):
    with session() as s:
        c = crud.get_company(s, company_id)
        if not c:
            raise HTTPException(status_code=404, detail="company_not_found")
        return c


@app.post("/api/people", response_model=PersonRead)
def api_create_person(payload: PersonCreate):
    with session() as s:
        if not crud.get_company(s, payload.company_id):
            raise HTTPException(status_code=400, detail="invalid_company_id")
        obj = Person(**payload.model_dump())
        obj = crud.create_person(s, obj)
        return obj


@app.get("/api/people", response_model=list[PersonRead])
def api_list_people(
    company_id: Optional[int] = None,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    with session() as s:
        return crud.list_people(s, company_id=company_id, query=q, limit=limit)


@app.get("/api/people/{person_id}", response_model=PersonRead)
def api_get_person(person_id: int):
    with session() as s:
        p = crud.get_person(s, person_id)
        if not p:
            raise HTTPException(status_code=404, detail="person_not_found")
        return p


@app.post("/api/org-nodes", response_model=OrgNodeRead)
def api_create_org_node(payload: OrgNodeCreate):
    with session() as s:
        if not crud.get_company(s, payload.company_id):
            raise HTTPException(status_code=400, detail="invalid_company_id")
        if payload.parent_id is not None and not crud.get_org_node(s, payload.parent_id):
            raise HTTPException(status_code=400, detail="invalid_parent_id")
        if payload.person_id is not None and not crud.get_person(s, payload.person_id):
            raise HTTPException(status_code=400, detail="invalid_person_id")

        obj = OrgNode(**payload.model_dump())
        obj = crud.create_org_node(s, obj)
        return OrgNodeRead(
            id=obj.id,
            company_id=obj.company_id,
            parent_id=obj.parent_id,
            node_type=obj.node_type,
            display_name=obj.display_name,
            sort_order=obj.sort_order,
            person_id=obj.person_id,
            has_children=crud.org_node_has_children(s, obj.id),
        )


@app.get("/api/companies/{company_id}/org-nodes", response_model=list[OrgNodeRead])
def api_list_org_children(company_id: int, parent_id: Optional[int] = None):
    with session() as s:
        if not crud.get_company(s, company_id):
            raise HTTPException(status_code=404, detail="company_not_found")
        nodes = crud.list_org_children(s, company_id=company_id, parent_id=parent_id)
        out: list[OrgNodeRead] = []
        for n in nodes:
            out.append(
                OrgNodeRead(
                    id=n.id,
                    company_id=n.company_id,
                    parent_id=n.parent_id,
                    node_type=n.node_type,
                    display_name=n.display_name,
                    sort_order=n.sort_order,
                    person_id=n.person_id,
                    has_children=crud.org_node_has_children(s, n.id),
                )
            )
        return out


@app.post("/api/news/import", response_model=NewsItemRead)
def api_import_news(payload: NewsItemCreate):
    with session() as s:
        if payload.company_id is not None and not crud.get_company(s, payload.company_id):
            raise HTTPException(status_code=400, detail="invalid_company_id")
        if payload.person_id is not None and not crud.get_person(s, payload.person_id):
            raise HTTPException(status_code=400, detail="invalid_person_id")
        obj = NewsItem(**payload.model_dump())
        obj = crud.upsert_news_item_by_url(s, obj)
        return obj


@app.get("/api/people/{person_id}/news", response_model=list[NewsItemRead])
def api_list_news_for_person(person_id: int, limit: int = Query(default=20, ge=1, le=200)):
    with session() as s:
        if not crud.get_person(s, person_id):
            raise HTTPException(status_code=404, detail="person_not_found")
        return crud.list_news_for_person(s, person_id, limit=limit)


@app.post("/api/relationships/recompute")
def api_recompute_relationships(payload: RecomputeRelationshipsRequest):
    with session() as s:
        if not crud.get_company(s, payload.company_id):
            raise HTTPException(status_code=404, detail="company_not_found")
        updated = crud.recompute_relationships(
            s,
            company_id=payload.company_id,
            half_life_days=payload.half_life_days,
        )
        return {"updated": updated}


@app.get("/api/companies/{company_id}/relationships", response_model=list[RelationshipRead])
def api_list_relationships(company_id: int, limit: int = Query(default=200, ge=1, le=2000)):
    with session() as s:
        if not crud.get_company(s, company_id):
            raise HTTPException(status_code=404, detail="company_not_found")
        stmt = (
            select(Relationship)
            .where(Relationship.company_id == company_id)
            .order_by(Relationship.score.desc())
            .limit(limit)
        )
        return list(s.exec(stmt).all())

