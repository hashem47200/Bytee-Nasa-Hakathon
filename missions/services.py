"""Exam grading, dual celestial progress calculation, and Bytee certificate issuing.
Grading and progress validation always happen strictly on the server.
"""
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from .models import Certificate, QuestionAttempt, QuizAttempt, UserProgress, Vehicle, pass_percent


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
    Passing enforces the strict 100% full-mark requirement (threshold = pass_percent() = 100).
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
    passed = bool(total) and percent >= threshold
    return GradeResult(total, correct, percent, passed, threshold, chosen, correct_ids)


def calculate_user_celestial_progress(user):
    """
    Calculates independent Mars and Moon exploration progress for a given user.
    Progress is determined by the percentage of vehicles whose exam has been passed with 100%.
    """
    if not user or not user.is_authenticated:
        return {
            'mars_percent': 0,
            'mars_passed': 0,
            'mars_total': Vehicle.objects.filter(category__slug='mars', is_published=True).count(),
            'mars_certified': False,
            'moon_percent': 0,
            'moon_passed': 0,
            'moon_total': Vehicle.objects.filter(category__slug='moon', is_published=True).count(),
            'moon_certified': False,
        }

    mars_vehicles = list(Vehicle.objects.filter(category__slug='mars', is_published=True).values_list('id', flat=True))
    moon_vehicles = list(Vehicle.objects.filter(category__slug='moon', is_published=True).values_list('id', flat=True))

    passed_vehicle_ids = set(
        QuizAttempt.objects.filter(
            user=user,
            passed=True,
            score_percent=100
        ).values_list('vehicle_id', flat=True).distinct()
    )

    mars_passed = len([v_id for v_id in mars_vehicles if v_id in passed_vehicle_ids])
    moon_passed = len([v_id for v_id in moon_vehicles if v_id in passed_vehicle_ids])

    mars_total = len(mars_vehicles) or 1
    moon_total = len(moon_vehicles) or 1

    mars_pct = (mars_passed * 100) // mars_total
    moon_pct = (moon_passed * 100) // moon_total

    mars_cert = Certificate.objects.filter(user=user, body_name='Mars').exists()
    moon_cert = Certificate.objects.filter(user=user, body_name='Moon').exists()

    return {
        'mars_percent': mars_pct,
        'mars_passed': mars_passed,
        'mars_total': mars_total,
        'mars_certified': mars_cert or mars_pct == 100,
        'moon_percent': moon_pct,
        'moon_passed': moon_passed,
        'moon_total': moon_total,
        'moon_certified': moon_cert or moon_pct == 100,
    }


@transaction.atomic
def record_attempt(user, vehicle, result):
    """
    Persist the exam attempt, record question logs, recalculate Mars/Moon progress,
    and unlock celestial certificates if 100% full-mark completion has been achieved.
    """
    attempt = QuizAttempt.objects.create(
        user=user,
        vehicle=vehicle,
        total_questions=result.total,
        correct_count=result.correct,
        score_percent=result.percent,
        pass_percent=result.threshold,
        passed=result.passed,
        answers={str(k): v for k, v in result.answers.items()},
    )

    progress, _ = UserProgress.objects.select_for_update().get_or_create(user=user)
    now = timezone.now()

    for q in vehicle.questions.prefetch_related('answers'):
        answer = next((a for a in q.answers.all() if a.id == result.answers.get(q.id)), None)
        is_correct = q.id in result.correct_ids
        QuestionAttempt.objects.create(
            user=user,
            question=q,
            selected_answer=answer,
            selected_text=answer.text if answer else '',
            is_correct=is_correct,
            attempted_at=now
        )
        progress.total_questions_answered += 1
        if is_correct:
            progress.total_correct_answers += 1
        else:
            progress.total_wrong_answers += 1

    # Recalculate celestial progress
    stats = calculate_user_celestial_progress(user)
    progress.mars_progress_percent = stats['mars_percent']
    progress.moon_progress_percent = stats['moon_percent']
    progress.mars_certified = stats['mars_certified']
    progress.moon_certified = stats['moon_certified']
    progress.save()

    # Issue Celestial Certificates upon 100% full-mark completion of all missions for that body
    name = (user.get_full_name() or user.get_username()).strip()[:80]
    issued_cert = None

    if stats['mars_percent'] == 100:
        cert, created = Certificate.objects.get_or_create(
            user=user,
            body_name='Mars',
            certificate_type='body',
            defaults={
                'recipient_name': name,
                'title': 'Mars Certificate of Exploration',
                'score_percent': 100,
                'quiz_attempt': attempt,
            }
        )
        if created:
            issued_cert = cert

    if stats['moon_percent'] == 100:
        cert, created = Certificate.objects.get_or_create(
            user=user,
            body_name='Moon',
            certificate_type='body',
            defaults={
                'recipient_name': name,
                'title': 'Moon Certificate of Exploration',
                'score_percent': 100,
                'quiz_attempt': attempt,
            }
        )
        if created:
            issued_cert = cert

    return attempt, issued_cert
