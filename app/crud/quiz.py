from sqlalchemy.orm import Session

from app.models.quiz import Quiz
from app.models.quiz_question import QuizQuestion
from app.models.quiz_choice import QuizChoice
from app.models.quiz_attempt import QuizAttempt
from app.models.quiz_answer import QuizAnswer


# =========================================================
# QUIZ
# =========================================================

class CRUDQuiz:

    model = Quiz

    def create(self, db: Session, data: dict):
        quiz = Quiz(**data)

        db.add(quiz)
        db.commit()
        db.refresh(quiz)

        return quiz

    def get(self, db: Session, quiz_id):
        return (
            db.query(Quiz)
            .filter(Quiz.id == quiz_id)
            .first()
        )

    def get_all(self, db: Session):
        return (
            db.query(Quiz)
            .all()
        )

    def delete(self, db: Session, quiz):
        db.delete(quiz)
        db.commit()

    def update(self, db: Session, quiz, data: dict):
        for key, value in data.items():
            setattr(quiz, key, value)

        db.commit()
        db.refresh(quiz)

        return quiz


quiz = CRUDQuiz()


# =========================================================
# QUESTIONS
# =========================================================

class CRUDQuizQuestion:

    model = QuizQuestion

    def create(self, db: Session, data: dict):
        question = QuizQuestion(**data)

        db.add(question)
        db.commit()
        db.refresh(question)

        return question

    def get(self, db: Session, question_id):
        return (
            db.query(QuizQuestion)
            .filter(QuizQuestion.id == question_id)
            .first()
        )

    def get_by_quiz(self, db: Session, quiz_id):
        return (
            db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz_id)
            .all()
        )


quiz_question = CRUDQuizQuestion()


# =========================================================
# CHOICES
# =========================================================

class CRUDQuizChoice:

    model = QuizChoice

    def create(self, db: Session, data: dict):
        choice = QuizChoice(**data)

        db.add(choice)
        db.commit()
        db.refresh(choice)

        return choice

    def get_by_question(self, db: Session, question_id):
        return (
            db.query(QuizChoice)
            .filter(QuizChoice.question_id == question_id)
            .all()
        )


quiz_choice = CRUDQuizChoice()


# =========================================================
# ATTEMPTS
# =========================================================

class CRUDQuizAttempt:

    model = QuizAttempt

    def create(self, db: Session, data: dict):
        attempt = QuizAttempt(**data)

        db.add(attempt)
        db.commit()
        db.refresh(attempt)

        return attempt

    def get(self, db: Session, attempt_id):
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.id == attempt_id)
            .first()
        )

    def get_by_student(self, db: Session, student_id):
        return (
            db.query(QuizAttempt)
            .filter(QuizAttempt.student_id == student_id)
            .all()
        )


quiz_attempt = CRUDQuizAttempt()


# =========================================================
# ANSWERS
# =========================================================

class CRUDQuizAnswer:

    model = QuizAnswer

    def create(self, db: Session, data: dict):
        answer = QuizAnswer(**data)

        db.add(answer)
        db.commit()
        db.refresh(answer)

        return answer

    def get_by_attempt(self, db: Session, attempt_id):
        return (
            db.query(QuizAnswer)
            .filter(QuizAnswer.attempt_id == attempt_id)
            .all()
        )


quiz_answer = CRUDQuizAnswer()