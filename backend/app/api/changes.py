from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.db import get_db
from app.models import ChangeEvent

router = APIRouter()


@router.get("")
def list_changes(
    event_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(ChangeEvent)
    if event_type:
        q = q.filter(ChangeEvent.event_type == event_type)
    if entity_type:
        q = q.filter(ChangeEvent.entity_type == entity_type)
    if entity_id:
        q = q.filter(ChangeEvent.entity_id == entity_id)
    events = q.order_by(desc(ChangeEvent.detected_at)).limit(limit).all()

    return {
        "changes": [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "event_type": e.event_type,
                "field_name": e.field_name,
                "old_value": e.old_value,
                "new_value": e.new_value,
                "description": e.description,
                "detected_at": e.detected_at.isoformat() if e.detected_at else None,
            }
            for e in events
        ],
        "count": len(events),
    }


@router.post("")
def create_change_event(data: dict, db: Session = Depends(get_db)):
    event = ChangeEvent(
        entity_type=data["entity_type"],
        entity_id=data["entity_id"],
        event_type=data["event_type"],
        field_name=data.get("field_name"),
        old_value=data.get("old_value"),
        new_value=data.get("new_value"),
        description=data.get("description"),
        source_url=data.get("source_url"),
    )
    db.add(event)
    db.commit()
    return {"status": "created", "id": event.id}
