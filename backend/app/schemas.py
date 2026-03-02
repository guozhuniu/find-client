from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from backend.app.models import OrgNodeType


class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    aliases: Optional[str] = None


class CompanyRead(BaseModel):
    id: int
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    aliases: Optional[str] = None
    created_at: datetime


class PersonCreate(BaseModel):
    company_id: int
    name: str
    title: Optional[str] = None
    phones: Optional[str] = None
    emails: Optional[str] = None
    location: Optional[str] = None
    source_confidence: float = 0.5


class PersonRead(BaseModel):
    id: int
    company_id: int
    name: str
    title: Optional[str] = None
    phones: Optional[str] = None
    emails: Optional[str] = None
    location: Optional[str] = None
    source_confidence: float
    created_at: datetime


class OrgNodeCreate(BaseModel):
    company_id: int
    parent_id: Optional[int] = None
    node_type: OrgNodeType
    display_name: str
    sort_order: int = 0
    person_id: Optional[int] = None


class OrgNodeRead(BaseModel):
    id: int
    company_id: int
    parent_id: Optional[int] = None
    node_type: OrgNodeType
    display_name: str
    sort_order: int
    person_id: Optional[int] = None
    has_children: bool = False


class NewsItemCreate(BaseModel):
    company_id: Optional[int] = None
    person_id: Optional[int] = None
    title: str
    url: str
    publisher: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    raw_text: Optional[str] = None
    relevance_score: float = 0.5


class NewsItemRead(BaseModel):
    id: int
    company_id: Optional[int] = None
    person_id: Optional[int] = None
    title: str
    url: str
    publisher: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    relevance_score: float
    created_at: datetime


class RelationshipRead(BaseModel):
    id: int
    company_id: int
    person_a_id: int
    person_b_id: int
    score: float
    evidence: Optional[str] = None
    updated_at: datetime


class RecomputeRelationshipsRequest(BaseModel):
    company_id: int
    half_life_days: int = Field(default=180, ge=1, le=3650)

