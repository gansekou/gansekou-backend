from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate


class CRUDUser(CRUDBase[User]):
    def get_by_firebase_uid(self, db: Session, firebase_uid: str):
        return db.query(User).filter(User.firebase_uid == firebase_uid).first()

    def get_by_email(self, db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    def get_by_phone(self, db: Session, phone: str):
        return db.query(User).filter(User.phone == phone).first()

    def create_user(self, db: Session, user_in: UserCreate):
        return self.create(db, user_in)


user = CRUDUser(User)