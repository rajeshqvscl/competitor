import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.db import get_db
from app.models import Alert, AlertNotification, ChangeEvent, Company, Category, Region

router = APIRouter()


@router.get("")
def list_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).options(
        joinedload(Alert.company),
        joinedload(Alert.category),
        joinedload(Alert.region),
    ).order_by(desc(Alert.created_at)).all()

    result = []
    for a in alerts:
        unread = db.query(AlertNotification).filter(
            AlertNotification.alert_id == a.id,
            AlertNotification.is_read == False,
        ).count()
        result.append({
            "id": a.id,
            "name": a.name,
            "company_id": a.company_id,
            "company_name": a.company.name if a.company else None,
            "category_id": a.category_id,
            "category_name": a.category.name if a.category else None,
            "region_id": a.region_id,
            "region_name": a.region.name if a.region else None,
            "event_types": json.loads(a.event_types) if a.event_types else [],
            "is_active": a.is_active,
            "unread_count": unread,
            "last_checked": a.last_checked.isoformat() if a.last_checked else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return result


@router.get("/{alert_id}")
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    a = db.query(Alert).options(
        joinedload(Alert.company),
        joinedload(Alert.category),
        joinedload(Alert.region),
    ).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    notifications = db.query(AlertNotification).filter(
        AlertNotification.alert_id == alert_id
    ).order_by(desc(AlertNotification.created_at)).all()

    return {
        "id": a.id,
        "name": a.name,
        "company_id": a.company_id,
        "company_name": a.company.name if a.company else None,
        "category_id": a.category_id,
        "category_name": a.category.name if a.category else None,
        "region_id": a.region_id,
        "region_name": a.region.name if a.region else None,
        "event_types": json.loads(a.event_types) if a.event_types else [],
        "is_active": a.is_active,
        "last_checked": a.last_checked.isoformat() if a.last_checked else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "notifications": [
            {
                "id": n.id,
                "message": n.message,
                "is_read": n.is_read,
                "change_event_id": n.change_event_id,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ],
    }


@router.post("")
def create_alert(data: dict, db: Session = Depends(get_db)):
    alert = Alert(
        name=data["name"],
        company_id=data.get("company_id"),
        category_id=data.get("category_id"),
        region_id=data.get("region_id"),
        event_types=json.dumps(data.get("event_types", [])),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"status": "created", "id": alert.id}


@router.put("/{alert_id}")
def update_alert(alert_id: int, data: dict, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if "name" in data:
        alert.name = data["name"]
    if "is_active" in data:
        alert.is_active = data["is_active"]
    if "event_types" in data:
        alert.event_types = json.dumps(data["event_types"])
    db.commit()
    return {"status": "updated"}


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"status": "deleted"}


@router.post("/{alert_id}/mark-read")
def mark_notifications_read(alert_id: int, db: Session = Depends(get_db)):
    db.query(AlertNotification).filter(
        AlertNotification.alert_id == alert_id,
        AlertNotification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"status": "marked_read"}
