from typing import Type, TypeVar, Generic
from sqlalchemy.orm import Session

from app.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id):
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in):
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def update(self, db: Session, db_obj, obj_in):
        obj_data = obj_in.model_dump(exclude_unset=True)

        for field, value in obj_data.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(self, db: Session, id):
        db_obj = self.get(db, id)

        if not db_obj:
            return None

        db.delete(db_obj)
        db.commit()

        return db_obj