"""migrate content quizzes to quizzes and normalize content types

Revision ID: f3a1c9d2e7b4
Revises: 4882ace4598d
Create Date: 2026-05-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "f3a1c9d2e7b4"
down_revision: Union[str, Sequence[str], None] = "4882ace4598d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


QUIZ_TYPES = (
    "'QUIZ','QUIZZ','QUIZZES','QCM','EVALUATION',"
    "'EVALUATION_INTERACTIVE','INTERACTIVE_ASSESSMENT'"
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'quizzes' AND column_name = 'course_id'
            ) THEN
                ALTER TABLE quizzes ADD COLUMN course_id UUID NULL;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_quizzes_course_id_contents'
            ) THEN
                ALTER TABLE quizzes
                ADD CONSTRAINT fk_quizzes_course_id_contents
                FOREIGN KEY (course_id) REFERENCES contents(id);
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'ix_quizzes_course_id'
            ) THEN
                CREATE INDEX ix_quizzes_course_id ON quizzes(course_id);
            END IF;
        END $$;
        """
    )

    op.execute(
        f"""
        INSERT INTO quizzes (
            id,
            content_id,
            course_id,
            author_id,
            subject_id,
            level_id,
            title,
            description,
            language,
            difficulty_level,
            quiz_type,
            status,
            is_premium,
            is_randomized,
            allow_retry,
            passing_score,
            estimated_duration_minutes,
            total_attempts,
            total_questions,
            created_at,
            updated_at
        )
        SELECT
            c.id,
            c.id,
            linked_course.id,
            c.author_id,
            c.subject_id,
            c.level_id,
            COALESCE(NULLIF(ct.title, ''), 'Quiz'),
            ct.description,
            COALESCE(ct.language, 'FR'),
            c.difficulty_level,
            'QCM',
            CASE WHEN c.status = 'APPROVED' THEN 'PUBLISHED' ELSE COALESCE(c.status, 'PUBLISHED') END,
            COALESCE(c.is_premium, false),
            false,
            true,
            50,
            c.estimated_duration_minutes,
            0,
            0,
            c.created_at,
            c.updated_at
        FROM contents c
        LEFT JOIN LATERAL (
            SELECT title, description, language
            FROM content_translations
            WHERE content_id = c.id
            ORDER BY CASE WHEN language = 'FR' THEN 0 ELSE 1 END, created_at ASC
            LIMIT 1
        ) ct ON true
        LEFT JOIN LATERAL (
            SELECT course.id
            FROM contents course
            LEFT JOIN LATERAL (
                SELECT title
                FROM content_translations
                WHERE content_id = course.id
                ORDER BY CASE WHEN language = COALESCE(ct.language, 'FR') THEN 0 ELSE 1 END, created_at ASC
                LIMIT 1
            ) course_title ON true
            WHERE course.content_type IN ('COURS', 'COURSE')
              AND course.subject_id = c.subject_id
              AND course.level_id = c.level_id
              AND (course.author_id = c.author_id OR c.author_id IS NULL)
              AND lower(regexp_replace(COALESCE(course_title.title, ''), '[^a-zA-Z0-9]+', '', 'g')) =
                  lower(regexp_replace(regexp_replace(COALESCE(ct.title, ''), '^(quiz|qcm)[[:space:][:punct:]]+', '', 'i'), '[^a-zA-Z0-9]+', '', 'g'))
            ORDER BY CASE WHEN course.author_id = c.author_id THEN 0 ELSE 1 END, course.created_at DESC
            LIMIT 1
        ) linked_course ON true
        WHERE upper(c.content_type) IN ({QUIZ_TYPES})
          AND NOT EXISTS (
              SELECT 1 FROM quizzes q WHERE q.content_id = c.id OR q.id = c.id
          );
        """
    )

    op.execute(
        f"""
        UPDATE contents
        SET status = 'ARCHIVED'
        WHERE upper(content_type) IN ({QUIZ_TYPES});
        """
    )

    op.execute(
        """
        UPDATE contents
        SET content_type = CASE
            WHEN upper(content_type) IN ('EXERCISE', 'EXERCICE') THEN 'EXERCICE'
            WHEN upper(content_type) IN ('SUJET', 'EPREUVE', 'EXAM') THEN 'SUJET'
            WHEN upper(content_type) IN ('COURS', 'COURSE', 'PDF', 'VIDEO', 'AUDIO', 'DOCUMENT', 'TOPIC', 'AUTRE') THEN 'COURS'
            WHEN upper(content_type) IN ('QUIZ', 'QUIZZ', 'QUIZZES', 'QCM', 'EVALUATION', 'EVALUATION_INTERACTIVE', 'INTERACTIVE_ASSESSMENT') THEN 'COURS'
            ELSE 'COURS'
        END
        WHERE content_type IS NULL
           OR upper(content_type) NOT IN ('COURS', 'EXERCICE', 'SUJET');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'quizzes' AND column_name = 'course_id'
            ) THEN
                ALTER TABLE quizzes DROP COLUMN course_id;
            END IF;
        END $$;
        """
    )
