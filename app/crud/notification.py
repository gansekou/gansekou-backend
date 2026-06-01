from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.notification import Notification


class CRUDNotification(CRUDBase[Notification]):
    def get_by_user(self, db: Session, user_id):
        return db.query(Notification).filter(Notification.user_id == user_id).all()

    def mark_as_read(self, db: Session, notification_id):
        notification = self.get(db, notification_id)

        if not notification:
            return None

        notification.is_read = True

        db.commit()
        db.refresh(notification)

        return notification


notification = CRUDNotification(Notification)