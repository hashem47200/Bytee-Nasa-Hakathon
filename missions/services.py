"""Exam grading and certificate issuing. Grading always happens on the server."""
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from .models import Certificate, QuestionAttempt, QuizAttempt, UserProgress, pass_percent


@dataclass
class GradeResult:
    total: int
    correct: int
    percent: int
    passed: bool
    threshold: int
    answers: dict = field(default_factory=dict)       # {question_id: answer_id}
    correct_ids: set = field(default_factory=set)     # question ids answered correctly


def grade(vehicle, selections):
    """
    selections: {question_id: answer_id}. Unknown or missing selections count as wrong.
    Passing uses integer maths (correct*100 >= total*threshold) so 59.9% can never round up to a pass.
    """
    questions = list(vehicle.questions.prefetch_related('answers'))
    threshold = pass_percent()
    correct_ids, chosen = set(), {}
    for q in questions:
        sel = selections.get(q.id)
        answer = next((a for a in q.answers.all() if a.id == sel), None)
        if answer:
            chosen[q.id] = answer.id
            if answer.is_correct:
                correct_ids.add(q.id)
    total, correct = len(questions), len(correct_ids)
    percent = (correct * 100) // total if total else 0
    passed = bool(total) and correct * 100 >= total * threshold
    return GradeResult(total, correct, percent, passed, threshold, chosen, correct_ids)


@transaction.atomic
def record_attempt(user, vehicle, result):
    """Persist the attempt, update progress counters and issue/refresh the certificate on a pass."""
    attempt = QuizAttempt.objects.create(
        user=user, vehicle=vehicle, total_questions=result.total, correct_count=result.correct,
        score_percent=result.percent, pass_percent=result.threshold, passed=result.passed,
        answers={str(k): v for k, v in result.answers.items()},
    )
    progress, _ = UserProgress.objects.select_for_update().get_or_create(user=user)
    now = timezone.now()
    for q in vehicle.questions.prefetch_related('answers'):
        answer = next((a for a in q.answers.all() if a.id == result.answers.get(q.id)), None)
        is_correct = q.id in result.correct_ids
        QuestionAttempt.objects.create(
            user=user, question=q, selected_answer=answer, selected_text=answer.text if answer else '',
            is_correct=is_correct, attempted_at=now)
        progress.total_questions_answered += 1
        if is_correct:
            progress.total_correct_answers += 1
        else:
            progress.total_wrong_answers += 1
    progress.save()

    certificate = None
    if result.passed:
        name = (user.get_full_name() or user.get_username()).strip()[:80]
        certificate, created = Certificate.objects.get_or_create(
            user=user, vehicle=vehicle,
            defaults={'recipient_name': name, 'score_percent': result.percent, 'quiz_attempt': attempt})
        if not created and result.percent > certificate.score_percent:
            certificate.score_percent = result.percent
            certificate.quiz_attempt = attempt
            certificate.save(update_fields=['score_percent', 'quiz_attempt'])
    return attempt, certificate
