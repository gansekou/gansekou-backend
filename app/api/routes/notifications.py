from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.crud.notification import notification
from app.core.security import get_current_user, require_roles
from app.core.websocket_manager import websocket_manager

router = APIRouter()

ADMIN_ROLES = ["ADMIN", "PROMOTEUR", "ADMINISTRATEUR"]


@router.post("/", response_model=NotificationResponse)
def create_notification(
    payload: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    created = notification.create(db, payload)
    background_tasks.add_task(
        websocket_manager.send_to_user,
        created.user_id,
        {
            "type": created.type or "NOTIFICATION",
            "title": created.title,
            "message": created.message,
            "notification_id": str(created.id),
        },
    )
    return created


@router.get("/", response_model=list[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return notification.get_all(db)


@router.get("/me", response_model=list[NotificationResponse])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return notification.get_by_user(db, current_user.id)


@router.get("/user/{user_id}", response_model=list[NotificationResponse])
def get_user_notifications(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    return notification.get_by_user(db, user_id)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_notification = notification.get(db, notification_id)

    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    if current_user.role not in ADMIN_ROLES and db_notification.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez marquer comme lue que vos propres notifications",
        )

    return notification.mark_as_read(db, notification_id)


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_notification = notification.get(db, notification_id)

    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    if current_user.role not in ADMIN_ROLES and db_notification.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez consulter que vos propres notifications",
        )

    return db_notification


@router.put("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: UUID,
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(ADMIN_ROLES)),
):
    db_notification = notification.get(db, notification_id)

    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    return notification.update(db, db_notification, payload)


@router.delete("/{notification_id}", response_model=NotificationResponse)
def delete_notification(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    db_notification = notification.get(db, notification_id)

    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    if current_user.role not in ADMIN_ROLES and db_notification.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez supprimer que vos propres notifications",
        )

    return notification.delete(db, notification_id)
