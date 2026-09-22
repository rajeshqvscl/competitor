import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from app.db import get_db
from app.models import SavedAnalysis

router = APIRouter()


@router.get("")
def list_saved_analyses(db: Session = Depends(get_db)):
    analyses = db.query(SavedAnalysis).order_by(desc(SavedAnalysis.updated_at)).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "filters": json.loads(a.filters) if a.filters else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "updated_at": a.updated_at.isoformat() if a.updated_at else None,
        }
        for a in analyses
    ]


@router.get("/{analysis_id}")
def get_saved_analysis(analysis_id: int, db: Session = Depends(get_db)):
    a = db.query(SavedAnalysis).filter(SavedAnalysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "filters": json.loads(a.filters) if a.filters else None,
        "results": json.loads(a.results) if a.results else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


@router.post("")
def save_analysis(data: dict, db: Session = Depends(get_db)):
    a = SavedAnalysis(
        name=data["name"],
        description=data.get("description"),
        filters=json.dumps(data.get("filters")),
        results=json.dumps(data.get("results")),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"status": "saved", "id": a.id}


@router.delete("/{analysis_id}")
def delete_analysis(analysis_id: int, db: Session = Depends(get_db)):
    a = db.query(SavedAnalysis).filter(SavedAnalysis.id == analysis_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    db.delete(a)
    db.commit()
    return {"status": "deleted"}
