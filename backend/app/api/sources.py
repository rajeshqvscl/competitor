from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.db import get_db
from app.models import Source

router = APIRouter()


@router.get("")
def list_sources(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Source)
    if entity_type:
        q = q.filter(Source.entity_type == entity_type)
    if entity_id:
        q = q.filter(Source.entity_id == entity_id)
    return q.order_by(Source.created_at.desc()).limit(100).all()


@router.get("/{entity_type}/{entity_id}")
def get_entity_sources(entity_type: str, entity_id: int, db: Session = Depends(get_db)):
    sources = db.query(Source).filter(
        Source.entity_type == entity_type,
        Source.entity_id == entity_id,
    ).order_by(Source.created_at.desc()).all()
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "sources": sources,
        "count": len(sources),
    }
