import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.db import get_db
from app.models import ReviewQueue

router = APIRouter()


@router.get("")
def list_review_queue(
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ReviewQueue)
    if status:
        q = q.filter(ReviewQueue.status == status)
    if entity_type:
        q = q.filter(ReviewQueue.entity_type == entity_type)
    items = q.order_by(desc(ReviewQueue.created_at)).limit(100).all()

    return [
        {
            "id": item.id,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "action": item.action,
            "status": item.status,
            "data": json.loads(item.data) if item.data else None,
            "notes": item.notes,
            "reviewed_by": item.reviewed_by,
            "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]


@router.post("")
def create_review_item(data: dict, db: Session = Depends(get_db)):
    item = ReviewQueue(
        entity_type=data["entity_type"],
        entity_id=data.get("entity_id"),
        action=data["action"],
        data=json.dumps(data.get("data")),
        notes=data.get("notes"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "created", "id": item.id}


@router.put("/{item_id}/approve")
def approve_item(item_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(ReviewQueue).filter(ReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    item.status = "approved"
    item.reviewed_by = data.get("reviewed_by", "admin")
    db.commit()
    return {"status": "approved"}


@router.put("/{item_id}/reject")
def reject_item(item_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(ReviewQueue).filter(ReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    item.status = "rejected"
    item.reviewed_by = data.get("reviewed_by", "admin")
    item.notes = data.get("notes", item.notes)
    db.commit()
    return {"status": "rejected"}


@router.delete("/{item_id}")
def delete_review_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ReviewQueue).filter(ReviewQueue.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")
    db.delete(item)
    db.commit()
    return {"status": "deleted"}
