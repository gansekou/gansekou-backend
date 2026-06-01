from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.education_cycle import EducationCycleCreate, EducationCycleResponse
from app.schemas.level import LevelCreate, LevelResponse
from app.schemas.specialty import SpecialtyCreate, SpecialtyResponse
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.crud.education import education_cycle, level, specialty, subject
from app.core.security import require_roles

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


@router.post("/cycles", response_model=EducationCycleResponse)
def create_cycle(
    payload: EducationCycleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return education_cycle.create(db, payload)


@router.get("/cycles", response_model=list[EducationCycleResponse])
def get_cycles(db: Session = Depends(get_db)):
    return education_cycle.get_all(db)


@router.get("/cycles/{cycle_id}", response_model=EducationCycleResponse)
def get_cycle(cycle_id: UUID, db: Session = Depends(get_db)):
    db_cycle = education_cycle.get(db, cycle_id)
    if not db_cycle:
        raise HTTPException(status_code=404, detail="Cycle introuvable")
    return db_cycle


@router.put("/cycles/{cycle_id}", response_model=EducationCycleResponse)
def update_cycle(
    cycle_id: UUID,
    payload: EducationCycleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_cycle = education_cycle.get(db, cycle_id)
    if not db_cycle:
        raise HTTPException(status_code=404, detail="Cycle introuvable")
    return education_cycle.update(db, db_cycle, payload)


@router.delete("/cycles/{cycle_id}", response_model=EducationCycleResponse)
def delete_cycle(
    cycle_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_cycle = education_cycle.delete(db, cycle_id)
    if not db_cycle:
        raise HTTPException(status_code=404, detail="Cycle introuvable")
    return db_cycle


@router.post("/levels", response_model=LevelResponse)
def create_level(
    payload: LevelCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return level.create(db, payload)


@router.get("/levels", response_model=list[LevelResponse])
def get_levels(db: Session = Depends(get_db)):
    return level.get_all(db)


@router.get("/levels/{level_id}", response_model=LevelResponse)
def get_level(level_id: UUID, db: Session = Depends(get_db)):
    db_level = level.get(db, level_id)
    if not db_level:
        raise HTTPException(status_code=404, detail="Niveau introuvable")
    return db_level


@router.put("/levels/{level_id}", response_model=LevelResponse)
def update_level(
    level_id: UUID,
    payload: LevelCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_level = level.get(db, level_id)
    if not db_level:
        raise HTTPException(status_code=404, detail="Niveau introuvable")
    return level.update(db, db_level, payload)


@router.delete("/levels/{level_id}", response_model=LevelResponse)
def delete_level(
    level_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_level = level.delete(db, level_id)
    if not db_level:
        raise HTTPException(status_code=404, detail="Niveau introuvable")
    return db_level


@router.post("/specialties", response_model=SpecialtyResponse)
def create_specialty(
    payload: SpecialtyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return specialty.create(db, payload)


@router.get("/specialties", response_model=list[SpecialtyResponse])
def get_specialties(db: Session = Depends(get_db)):
    return specialty.get_all(db)


@router.get("/specialties/{specialty_id}", response_model=SpecialtyResponse)
def get_specialty(specialty_id: UUID, db: Session = Depends(get_db)):
    db_specialty = specialty.get(db, specialty_id)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Spécialité introuvable")
    return db_specialty


@router.put("/specialties/{specialty_id}", response_model=SpecialtyResponse)
def update_specialty(
    specialty_id: UUID,
    payload: SpecialtyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_specialty = specialty.get(db, specialty_id)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Spécialité introuvable")
    return specialty.update(db, db_specialty, payload)


@router.delete("/specialties/{specialty_id}", response_model=SpecialtyResponse)
def delete_specialty(
    specialty_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_specialty = specialty.delete(db, specialty_id)
    if not db_specialty:
        raise HTTPException(status_code=404, detail="Spécialité introuvable")
    return db_specialty


@router.post("/subjects", response_model=SubjectResponse)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return subject.create(db, payload)


@router.get("/subjects", response_model=list[SubjectResponse])
def get_subjects(db: Session = Depends(get_db)):
    return subject.get_all(db)


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: UUID, db: Session = Depends(get_db)):
    db_subject = subject.get(db, subject_id)
    if not db_subject:
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return db_subject


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: UUID,
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_subject = subject.get(db, subject_id)
    if not db_subject:
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return subject.update(db, db_subject, payload)


@router.delete("/subjects/{subject_id}", response_model=SubjectResponse)
def delete_subject(
    subject_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_subject = subject.delete(db, subject_id)
    if not db_subject:
        raise HTTPException(status_code=404, detail="Matière introuvable")
    return db_subject
