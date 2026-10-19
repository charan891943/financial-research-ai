from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.seed_service import SeedService

router = APIRouter(prefix="/seed", tags=["Seed Data"])

@router.post("")
def trigger_seed(db: Session = Depends(get_db)):
    session = SeedService.seed_workspace(db)
    return {
        "status": "success",
        "message": "Seeded 4 companies (TCS, Reliance, Infosys, HDFC Bank) with vector index and extracted metrics.",
        "session_id": session.id,
        "session_name": session.name
    }
