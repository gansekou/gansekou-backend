from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.device_session import DeviceSession
from app.models.sync_log import SyncLog


class CRUDDeviceSession(CRUDBase[DeviceSession]):
    def get_by_device_id(self, db: Session, device_id: str):
        return db.query(DeviceSession).filter(DeviceSession.device_id == device_id).first()

    def get_by_user(self, db: Session, user_id):
        return db.query(DeviceSession).filter(DeviceSession.user_id == user_id).all()


class CRUDSyncLog(CRUDBase[SyncLog]):
    def get_by_user(self, db: Session, user_id):
        return db.query(SyncLog).filter(SyncLog.user_id == user_id).all()

    def get_by_device_session(self, db: Session, device_session_id):
        return db.query(SyncLog).filter(SyncLog.device_session_id == device_session_id).all()


device_session = CRUDDeviceSession(DeviceSession)
sync_log = CRUDSyncLog(SyncLog)