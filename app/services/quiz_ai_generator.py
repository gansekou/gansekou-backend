import random


def generate_ai_quiz(payload):

    questions = []

    for i in range(payload.number_of_questions):

        correct_index = random.randint(0, 3)

        choices = []

        for j in range(4):

            choices.append({
                "choice_text": f"Réponse {j + 1}",
                "is_correct": j == correct_index,
            })

        question = {
            "question_text": f"Question IA {i + 1} sur {payload.title}",
            "explanation": "Explication pédagogique générée automatiquement.",
            "points": 1,
            "choices": choices,
        }

        questions.append(question)

    return {
        "title": payload.title,
        "description": f"Quiz IA généré automatiquement sur {payload.title}",
        "questions": questions,
    }