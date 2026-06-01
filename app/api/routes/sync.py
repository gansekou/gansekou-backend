from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.device_session import DeviceSessionCreate, DeviceSessionResponse
from app.schemas.sync_log import SyncLogCreate, SyncLogResponse
from app.crud.sync import device_session, sync_log
from app.crud.content import content
from app.crud.question import student_question
from app.core.security import get_current_user, require_roles
from app.core.premium import user_has_active_subscription

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


@router.post("/devices", response_model=DeviceSessionResponse)
def create_device_session(
    payload: DeviceSessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload.user_id = current_user.id

    existing = device_session.get_by_device_id(db, payload.device_id)

    if existing:
        if existing.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
            raise HTTPException(
                status_code=403,
                detail="Cet appareil n'appartient pas à votre compte",
            )
        return existing

    return device_session.create(db, payload)


@router.get("/devices/me", response_model=list[DeviceSessionResponse])
def get_my_devices(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return device_session.get_by_user(db, current_user.id)


@router.get("/devices/user/{user_id}", response_model=list[DeviceSessionResponse])
def get_user_devices(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return device_session.get_by_user(db, user_id)


@router.get("/devices/{device_id}", response_model=DeviceSessionResponse)
def get_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_device = device_session.get(db, device_id)

    if not db_device:
        raise HTTPException(status_code=404, detail="Appareil introuvable")

    if db_device.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez consulter que vos propres appareils",
        )

    return db_device


@router.put("/devices/{device_id}", response_model=DeviceSessionResponse)
def update_device(
    device_id: UUID,
    payload: DeviceSessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_device = device_session.get(db, device_id)

    if not db_device:
        raise HTTPException(status_code=404, detail="Appareil introuvable")

    if db_device.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez modifier que vos propres appareils",
        )

    if current_user.role not in ADMIN_ROLES:
        payload.user_id = current_user.id

    return device_session.update(db, db_device, payload)


@router.delete("/devices/{device_id}", response_model=DeviceSessionResponse)
def delete_device(
    device_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_device = device_session.get(db, device_id)

    if not db_device:
        raise HTTPException(status_code=404, detail="Appareil introuvable")

    if db_device.user_id != current_user.id and current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez supprimer que vos propres appareils",
        )

    return device_session.delete(db, device_id)


@router.post("/logs", response_model=SyncLogResponse)
def create_sync_log(
    payload: SyncLogCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload.user_id = current_user.id
    return sync_log.create(db, payload)


@router.get("/logs/me", response_model=list[SyncLogResponse])
def get_my_sync_logs(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return sync_log.get_by_user(db, current_user.id)


@router.get("/logs/user/{user_id}", response_model=list[SyncLogResponse])
def get_user_sync_logs(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return sync_log.get_by_user(db, user_id)


@router.get("/offline-package")
def get_offline_package(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    contents_query = db.query(content.model).filter(content.model.is_available_offline == True)

    if current_user.role == "ELEVE" and not user_has_active_subscription(db, current_user.id):
        contents_query = contents_query.filter(content.model.is_premium == False)

    return {
        "contents": contents_query.all(),
    }


@router.get("/unsynced-questions")
def get_unsynced_questions(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return student_question.get_unsynced(db)
