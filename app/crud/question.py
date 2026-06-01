from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.student_question import StudentQuestion
from app.models.ai_answer import AIAnswer
from app.models.teacher_answer import TeacherAnswer


class CRUDQuestion(CRUDBase[StudentQuestion]):
    def create(self, db: Session, obj_in):
        obj_data = obj_in.model_dump(
            exclude={"answer_mode", "requested_teacher_id"},
        )
        db_obj = StudentQuestion(**obj_data)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def get_by_student(self, db: Session, student_id):
        return db.query(StudentQuestion).filter(StudentQuestion.student_id == student_id).all()

    def get_by_status(self, db: Session, status: str):
        return db.query(StudentQuestion).filter(StudentQuestion.status == status).all()

    def get_unsynced(self, db: Session):
        return db.query(StudentQuestion).filter(StudentQuestion.sync_status != "SYNCED").all()

    def get_pending_teacher_questions(self, db: Session):
        return (
            db.query(StudentQuestion)
            .filter(StudentQuestion.teacher_requested == True)
            .filter(StudentQuestion.status == "REQUESTED_TEACHER")
            .all()
        )

    def request_teacher(self, db: Session, question_id):
        question = self.get(db, question_id)

        if not question:
            return None

        question.teacher_requested = True
        question.status = "REQUESTED_TEACHER"

        db.commit()
        db.refresh(question)

        return question

    def mark_synced(self, db: Session, question_id):
        question = self.get(db, question_id)

        if not question:
            return None

        question.sync_status = "SYNCED"

        db.commit()
        db.refresh(question)

        return question


student_question = CRUDQuestion(StudentQuestion)
ai_answer = CRUDBase(AIAnswer)
teacher_answer = CRUDBase(TeacherAnswer)
