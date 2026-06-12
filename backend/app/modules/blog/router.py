from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.core import BlogArticle
from app.modules.blog.schemas import (
    BlogArticleCreate,
    BlogArticleUpdate,
    BlogArticleResponse,
    BlogArticleListResponse,
)
from app.core.security import decode_token

router = APIRouter()


def _article_to_response(a: BlogArticle) -> BlogArticleResponse:
    return BlogArticleResponse(
        id=a.id,
        title=a.title,
        slug=a.slug,
        excerpt=a.excerpt,
        content=a.content,
        author=a.author,
        cover_image=a.cover_image,
        tags=a.tags,
        published=a.published,
        published_at=a.published_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.get("/articles", response_model=BlogArticleListResponse)
def list_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    tag: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = select(BlogArticle).where(BlogArticle.published == True)
    if tag:
        query = query.where(BlogArticle.tags.ilike(f"%{tag}%"))
    query = query.order_by(BlogArticle.published_at.desc()).offset(skip).limit(limit)
    articles = db.execute(query).scalars().all()
    total = db.execute(select(func.count(BlogArticle.id)).where(BlogArticle.published == True)).scalar() or 0
    return BlogArticleListResponse(
        articles=[_article_to_response(a) for a in articles],
        total=total,
    )


@router.get("/articles/{slug}", response_model=BlogArticleResponse)
def get_article(slug: str, db: Session = Depends(get_db)):
    article = db.execute(select(BlogArticle).where(BlogArticle.slug == slug)).scalar_one_or_none()
    if not article or not article.published:
        raise HTTPException(status_code=404, detail="Article not found")
    return _article_to_response(article)


@router.post("/articles", response_model=BlogArticleResponse)
def create_article(
    payload: BlogArticleCreate,
    db: Session = Depends(get_db),
    _token: dict = Depends(decode_token),
):
    existing = db.execute(select(BlogArticle).where(BlogArticle.slug == payload.slug)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")
    article = BlogArticle(
        title=payload.title,
        slug=payload.slug,
        excerpt=payload.excerpt,
        content=payload.content,
        author=payload.author,
        cover_image=payload.cover_image,
        tags=payload.tags,
        published=payload.published,
        published_at=datetime.now(UTC) if payload.published else None,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return _article_to_response(article)


@router.put("/articles/{article_id}", response_model=BlogArticleResponse)
def update_article(
    article_id: int,
    payload: BlogArticleUpdate,
    db: Session = Depends(get_db),
    _token: dict = Depends(decode_token),
):
    article = db.get(BlogArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(article, key, value)
    if "published" in update_data and update_data["published"] and not article.published_at:
        article.published_at = datetime.now(UTC)
    db.commit()
    db.refresh(article)
    return _article_to_response(article)


@router.delete("/articles/{article_id}")
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _token: dict = Depends(decode_token),
):
    article = db.get(BlogArticle, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
    return {"message": "Article deleted"}
