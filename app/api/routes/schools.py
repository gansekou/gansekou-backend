from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.address import AddressCreate, AddressResponse
from app.schemas.school import SchoolCreate, SchoolResponse
from app.crud.school import address, school
from app.core.security import get_current_user, require_roles

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


@router.post("/addresses", response_model=AddressResponse)
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return address.create(db, payload)


@router.get("/addresses", response_model=list[AddressResponse])
def get_addresses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return address.get_all(db, skip=skip, limit=limit)


@router.put("/addresses/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: UUID,
    payload: AddressCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_address = address.get(db, address_id)

    if not db_address:
        raise HTTPException(status_code=404, detail="Adresse introuvable")

    return address.update(db, db_address, payload)


@router.delete("/addresses/{address_id}", response_model=AddressResponse)
def delete_address(
    address_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_address = address.delete(db, address_id)

    if not db_address:
        raise HTTPException(status_code=404, detail="Adresse introuvable")

    return db_address


@router.post("/", response_model=SchoolResponse)
def create_school(
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return school.create(db, payload)


@router.get("/", response_model=list[SchoolResponse])
def get_schools(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return school.get_all(db, skip=skip, limit=limit)


@router.get("/{school_id}", response_model=SchoolResponse)
def get_school(
    school_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_school = school.get(db, school_id)

    if not db_school:
        raise HTTPException(status_code=404, detail="Établissement introuvable")

    return db_school


@router.put("/{school_id}", response_model=SchoolResponse)
def update_school(
    school_id: UUID,
    payload: SchoolCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_school = school.get(db, school_id)

    if not db_school:
        raise HTTPException(status_code=404, detail="Établissement introuvable")

    return school.update(db, db_school, payload)


@router.delete("/{school_id}", response_model=SchoolResponse)
def delete_school(
    school_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_school = school.delete(db, school_id)

    if not db_school:
        raise HTTPException(status_code=404, detail="Établissement introuvable")

    return db_school
