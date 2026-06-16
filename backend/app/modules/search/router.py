from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import or_
from app.db.session import SessionLocal
from app.db.models.core import Project, BlogArticle, NewsArticle
from app.core.security import decode_token

router = APIRouter()


class SearchResult(BaseModel):
    type: str
    id: int
    title: str
    snippet: str
    url: str


class SearchResponse(BaseModel):
    status: str
    query: str
    results: List[SearchResult]
    total: int


@router.get("", response_model=SearchResponse)
def search_site(q: str = Query("", min_length=1), token: dict = Depends(decode_token)):
    db = SessionLocal()
    try:
        company_id = token.get("company_id")
        results = []

        term = f"%{q}%"

        projects = db.query(Project).filter(
            Project.company_id == company_id,
            or_(
                Project.name.ilike(term),
                Project.location.ilike(term),
                Project.contractor_name.ilike(term),
                Project.project_type.ilike(term),
            )
        ).limit(10).all()

        for p in projects:
            results.append(SearchResult(
                type="project",
                id=p.id,
                title=p.name,
                snippet=f"{p.location} - {p.project_type} ({p.project_status})",
                url=f"/dashboard/projects"
            ))

        blogs = db.query(BlogArticle).filter(
            or_(
                BlogArticle.title.ilike(term),
                BlogArticle.content.ilike(term),
                BlogArticle.tags.ilike(term),
            ),
            BlogArticle.published == True
        ).limit(10).all()

        for b in blogs:
            snippet = b.excerpt or b.content[:200] if b.content else ""
            results.append(SearchResult(
                type="blog",
                id=b.id,
                title=b.title,
                snippet=snippet,
                url=f"/dashboard/blog"
            ))

        news = db.query(NewsArticle).filter(
            or_(
                NewsArticle.title.ilike(term),
                NewsArticle.content.ilike(term),
                NewsArticle.category.ilike(term),
            ),
            NewsArticle.published == True
        ).limit(10).all()

        for n in news:
            snippet = n.excerpt or n.content[:200] if n.content else ""
            results.append(SearchResult(
                type="news",
                id=n.id,
                title=n.title,
                snippet=snippet,
                url=f"/dashboard/news"
            ))

        return SearchResponse(
            status="success",
            query=q,
            results=results,
            total=len(results)
        )
    finally:
        db.close()
