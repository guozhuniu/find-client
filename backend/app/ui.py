from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.app import crud
from backend.app.db import session


router = APIRouter()
templates = Jinja2Templates(directory="backend/app/templates")


@router.get("/ui", response_class=HTMLResponse)
def ui_home(request: Request):
    with session() as s:
        companies = crud.list_companies(s, limit=200)
    return templates.TemplateResponse(
        request,
        "companies.html",
        {"companies": companies},
    )


@router.get("/ui/company/{company_id}", response_class=HTMLResponse)
def ui_company(request: Request, company_id: int):
    with session() as s:
        company = crud.get_company(s, company_id)
        if not company:
            return HTMLResponse("<h3>公司不存在</h3>", status_code=404)
        roots = crud.list_org_children(s, company_id=company_id, parent_id=None)
        has_children = {n.id: crud.org_node_has_children(s, n.id) for n in roots if n.id is not None}
    return templates.TemplateResponse(
        request,
        "company.html",
        {"company": company, "roots": roots, "has_children": has_children},
    )


@router.get("/ui/company/{company_id}/children", response_class=HTMLResponse)
def ui_children(request: Request, company_id: int, parent_id: int):
    with session() as s:
        children = crud.list_org_children(s, company_id=company_id, parent_id=parent_id)
        has_children = {n.id: crud.org_node_has_children(s, n.id) for n in children if n.id is not None}
    return templates.TemplateResponse(
        request,
        "org_children.html",
        {"company_id": company_id, "children": children, "has_children": has_children},
    )


@router.get("/ui/person/{person_id}", response_class=HTMLResponse)
def ui_person_panel(request: Request, person_id: int):
    with session() as s:
        person = crud.get_person(s, person_id)
        if not person:
            return HTMLResponse("<div class='muted'>人员不存在</div>", status_code=404)
        news = crud.list_news_for_person(s, person_id, limit=5)
    return templates.TemplateResponse(
        request,
        "person_panel.html",
        {"person": person, "news": news},
    )

