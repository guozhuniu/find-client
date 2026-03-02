from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class OrgNodeType(str, Enum):
    department = "department"
    role = "role"
    person = "person"


class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    industry: Optional[str] = Field(default=None, index=True)
    website: Optional[str] = None
    aliases: Optional[str] = None  # 逗号分隔，先用简单形态
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Person(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True, foreign_key="company.id")
    name: str = Field(index=True)
    title: Optional[str] = Field(default=None, index=True)
    phones: Optional[str] = None  # JSON 字符串（后续可改成 JSONB）
    emails: Optional[str] = None
    location: Optional[str] = None
    source_confidence: float = 0.5
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrgNode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True, foreign_key="company.id")
    parent_id: Optional[int] = Field(default=None, index=True, foreign_key="orgnode.id")

    node_type: OrgNodeType = Field(index=True)
    display_name: str
    sort_order: int = 0

    person_id: Optional[int] = Field(default=None, index=True, foreign_key="person.id")


class NewsItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: Optional[int] = Field(default=None, index=True, foreign_key="company.id")
    person_id: Optional[int] = Field(default=None, index=True, foreign_key="person.id")

    title: str
    url: str = Field(index=True)
    publisher: Optional[str] = Field(default=None, index=True)
    published_at: Optional[datetime] = Field(default=None, index=True)
    summary: Optional[str] = None
    raw_text: Optional[str] = None
    relevance_score: float = 0.5

    created_at: datetime = Field(default_factory=datetime.utcnow)


class NewsPersonMention(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    news_id: int = Field(index=True, foreign_key="newsitem.id")
    person_id: int = Field(index=True, foreign_key="person.id")
    mention_count: int = Field(default=1)


class Relationship(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(index=True, foreign_key="company.id")
    person_a_id: int = Field(index=True, foreign_key="person.id")
    person_b_id: int = Field(index=True, foreign_key="person.id")
    score: float = Field(index=True)
    evidence: Optional[str] = None  # JSON 字符串：文章ID、组织距离等
    updated_at: datetime = Field(default_factory=datetime.utcnow)

