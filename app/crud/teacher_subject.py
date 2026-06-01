from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.teacher_subject import TeacherSubject


class CRUDTeacherSubject(CRUDBase[TeacherSubject]):
    def get_by_teacher(self, db: Session, teacher_id):
        return db.query(TeacherSubject).filter(
            TeacherSubject.teacher_id == teacher_id
        ).all()

    def get_matching_teachers(self, db: Session, subject_id):
        return db.query(TeacherSubject).filter(
            TeacherSubject.subject_id == subject_id
        ).all()


teacher_subject = CRUDTeacherSubject(TeacherSubject)