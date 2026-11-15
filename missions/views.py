import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models, transaction
from django.middleware.csrf import get_token
from django.urls import reverse

from .models import (
    Category, Vehicle, VehicleSpec, VehicleImage, Story,
    Question, Answer, QuizAttempt, Certificate,
    UserProgress, QuestionAttempt, pass_percent
)
from .forms import CrewLoginForm, CrewRegisterForm
from .services import grade, record_attempt
from .pdf import certificate_pdf

User = get_user_model()


# --------------------------------------------------------------------------
# Multi-Page Editorial & Educational Views
# --------------------------------------------------------------------------

def home_view(request):
    """
    Main Mission Control Hub.
    Displays category toggle bar (Mars, Moon, Space), live progress tracking,
    and mission cards with instant client-side filtering.
    """
    categories = list(Category.objects.filter(is_active=True).order_by('order', 'name'))
    vehicles = list(
        Vehicle.objects.filter(is_published=True)
        .select_related('category')
        .prefetch_related('questions')
        .order_by('category__order', 'order', 'id')
    )

    total = len(vehicles)
    earned = 0
    overall_percent = 0

    user_certs = {}
    best_scores = {}
    if request.user.is_authenticated:
        for cert in Certificate.objects.filter(user=request.user).select_related('vehicle'):
            user_certs[cert.vehicle_id] = cert
        for att in QuizAttempt.objects.filter(user=request.user):
            cur = best_scores.get(att.vehicle_id, 0)
            if att.score_percent > cur:
                best_scores[att.vehicle_id] = att.score_percent
        earned = len(user_certs)
        overall_percent = (earned * 100) // total if total else 0

    cat_list = []
    for cat in categories:
        cat_vehicles = [v for v in vehicles if v.category_id == cat.id]
        cat_total = len(cat_vehicles)
        cat_earned = sum(1 for v in cat_vehicles if v.id in user_certs)
        cat_percent = (cat_earned * 100) // cat_total if cat_total else 0

        card_list = []
        for v in cat_vehicles:
            v.certificate = user_certs.get(v.id)
            v.best_score = best_scores.get(v.id)
            card_list.append(v)

        cat.total = cat_total
        cat.earned = cat_earned
        cat.percent = cat_percent
        cat.card_list = card_list
        cat_list.append(cat)

    # Prepare 3D interactive viewer planet telemetry data (Moon and Mars)
    planet_viewer_data = {
        'mars': {
            'name': 'Mars',
            'texture': '/static/images/planets/mars-texture.jpg',
            'description': 'Real topography texture with historical landing sites and rover traverses across the Martian surface.',
            'vehicles': [
                {
                    'slug': v.slug,
                    'name': v.name,
                    'lat': v.surface_lat if v.surface_lat is not None else 10.0,
                    'lon': v.surface_lon if v.surface_lon is not None else -20.0,
                    'coords': v.coordinates or 'Martian Surface',
                    'date': (v.landing_date or v.launch_date).strftime('%b %d, %Y') if (v.landing_date or v.launch_date) else 'Active',
                    'url': v.get_absolute_url(),
                    'quiz_url': v.get_quiz_url(),
                }
                for v in vehicles if v.category.slug == 'mars'
            ]
        },
        'moon': {
            'name': 'Moon',
            'texture': '/static/images/planets/moon-texture.jpg',
            'description': 'High-resolution lunar surface texture with Apollo landing modules and Surveyor robotic probe coordinates.',
            'vehicles': [
                {
                    'slug': v.slug,
                    'name': v.name,
                    'lat': v.surface_lat if v.surface_lat is not None else 5.0,
                    'lon': v.surface_lon if v.surface_lon is not None else 15.0,
                    'coords': v.coordinates or 'Lunar Surface',
                    'date': (v.landing_date or v.launch_date).strftime('%b %d, %Y') if (v.landing_date or v.launch_date) else '1969',
                    'url': v.get_absolute_url(),
                    'quiz_url': v.get_quiz_url(),
                }
                for v in vehicles if v.category.slug == 'moon'
            ]
        },
        'space': {
            'name': 'Deep Space',
            'texture': '/static/images/planets/space-texture.jpg',
            'description': 'Interstellar transit trajectories, Sun-Earth L2 Lagrange orbits, and heliocentric flight paths across deep space.',
            'vehicles': [
                {
                    'slug': v.slug,
                    'name': v.name,
                    'lat': v.surface_lat if v.surface_lat is not None else 0.0,
                    'lon': v.surface_lon if v.surface_lon is not None else 0.0,
                    'coords': v.coordinates or 'Deep Space',
                    'date': (v.landing_date or v.launch_date).strftime('%b %d, %Y') if (v.landing_date or v.launch_date) else 'Operating',
                    'url': v.get_absolute_url(),
                    'quiz_url': v.get_quiz_url(),
                }
                for v in vehicles if v.category.slug == 'space'
            ]
        }
    }

    context = {
        'total': total,
        'earned': earned,
        'overall_percent': overall_percent,
        'pass_percent': pass_percent(),
        'categories': cat_list,
        'planet_viewer_json': json.dumps(planet_viewer_data),
    }
    return render(request, 'missions/home.html', context)


def vehicle_detail_view(request, slug):
    """
    Clean editorial story layout with vehicle specs and historical narrative.
    Ends with the prominent CTA: 'Launch Mission Exam 🚀'.
    Deep space craft are visually isolated from planetary terrain.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('category').prefetch_related('specs', 'stories', 'questions'),
        slug=slug, is_published=True
    )
    category = vehicle.category
    deep_space = category.is_deep_space
    question_total = vehicle.questions.count()
    threshold = pass_percent()

    certificate = None
    if request.user.is_authenticated:
        certificate = Certificate.objects.filter(user=request.user, vehicle=vehicle).first()

    context = {
        'vehicle': vehicle,
        'category': category,
        'deep_space': deep_space,
        'question_total': question_total,
        'pass_percent': threshold,
        'certificate': certificate,
    }
    return render(request, 'missions/vehicle_detail.html', context)


def vehicle_quiz_view(request, slug):
    """
    Dedicated Exam Page with 60% Passing Threshold.
    GET: Displays the vehicle's questions in a clean, step-by-step card layout.
    POST: Evaluates score against 60% mark.
      - < 60%: Friendly telemetry failure message with clear 'Retake Exam' button.
      - >= 60%: Mission success badge + instant access to download personalized certificate.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related('category').prefetch_related('questions__answers'),
        slug=slug, is_published=True
    )
    questions = list(vehicle.questions.all().order_by('order', 'id'))
    threshold = pass_percent()

    if request.method == 'GET':
        return render(request, 'missions/quiz.html', {
            'vehicle': vehicle,
            'questions': questions,
            'pass_percent': threshold,
        })

    # Evaluate exam submission
    selections = {}
    for q in questions:
        val = request.POST.get(f'q_{q.id}')
        if val and val.isdigit():
            selections[q.id] = int(val)

    if len(selections) < len(questions):
        return render(request, 'missions/quiz.html', {
            'vehicle': vehicle,
            'questions': questions,
            'pass_percent': threshold,
            'error': 'Telemetry incomplete: please choose an answer for all mission questions before submitting.',
            'selected': selections,
        })

    result = grade(vehicle, selections)

    if request.user.is_authenticated:
        attempt, certificate = record_attempt(request.user, vehicle, result)
    else:
        # Mock attempt for unauthenticated explorer
        class MockAttempt:
            total_questions = result.total
            correct_count = result.correct
            score_percent = result.percent
            pass_percent = result.threshold
            passed = result.passed
        attempt = MockAttempt()
        certificate = None

    review = []
    for q in questions:
        sel_id = selections.get(q.id)
        sel_ans = next((a for a in q.answers.all() if a.id == sel_id), None)
        corr_ans = next((a for a in q.answers.all() if a.is_correct), None)
        ok = (q.id in result.correct_ids)
        review.append({
            'question': q,
            'selected': sel_ans,
            'correct': corr_ans,
            'ok': ok,
            'hint': q.hint,
        })

    return render(request, 'missions/quiz_result.html', {
        'vehicle': vehicle,
        'attempt': attempt,
        'certificate': certificate,
        'review': review,
    })


def certificate_view(request):
    """
    Unlocked achievement screen for certified space explorers.
    Shows the certificate gallery and full print/download canvas.
    """
    total_missions = Vehicle.objects.filter(is_published=True).count()

    if not request.user.is_authenticated:
        return render(request, 'missions/certificate.html', {
            'cert': None,
            'pass_percent': pass_percent(),
            'total': total_missions,
        })

    certificates = list(Certificate.objects.filter(user=request.user).select_related('vehicle').order_by('-issued_at'))
    if not certificates:
        return render(request, 'missions/certificate.html', {
            'cert': None,
            'certificates': [],
            'total': total_missions,
            'pass_percent': pass_percent(),
        })

    mission_slug = request.GET.get('mission')
    selected_cert = None
    if mission_slug:
        selected_cert = next((c for c in certificates if c.vehicle.slug == mission_slug), None)
    if not selected_cert:
        selected_cert = certificates[0]

    return render(request, 'missions/certificate.html', {
        'cert': selected_cert,
        'certificates': certificates,
        'total': total_missions,
        'owner': True,
        'auto_print': request.GET.get('print') == '1',
    })


def certificate_download_view(request, code):
    """
    Streams a crisp, high-resolution vector PDF of the official certificate.
    """
    cert = get_object_or_404(Certificate.objects.select_related('vehicle', 'user'), code=code)
    pdf_bytes = certificate_pdf(cert)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="NASA_Certificate_{cert.code}.pdf"'
    return response


@require_POST
def certificate_rename_view(request, code):
    """
    Allows certificate recipient to update the printed name on their credential.
    """
    if not request.user.is_authenticated:
        return redirect('login')
    cert = get_object_or_404(Certificate, code=code, user=request.user)
    new_name = request.POST.get('recipient_name', '').strip()[:80]
    if new_name:
        cert.recipient_name = new_name
        cert.save(update_fields=['recipient_name'])
        messages.success(request, f"Certificate recipient updated to {new_name}.")
    return redirect(f"{reverse('certificate')}?mission={cert.vehicle.slug}")


# --------------------------------------------------------------------------
# Authentication Views
# --------------------------------------------------------------------------

def crew_login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('home')
    if request.method == 'POST':
        form = CrewLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, Commander {user.username}!")
            return redirect(next_url)
    else:
        form = CrewLoginForm(request)
    return render(request, 'registration/login.html', {'form': form, 'next': next_url})


def crew_register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    next_url = request.GET.get('next') or request.POST.get('next') or reverse('home')
    if request.method == 'POST':
        form = CrewRegisterForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            UserProgress.objects.create(user=user)
            login(request, user)
            messages.success(request, f"Crew registration confirmed! Welcome aboard, {user.username}.")
            return redirect(next_url)
    else:
        form = CrewRegisterForm()
    return render(request, 'registration/register.html', {'form': form, 'next': next_url})


@require_http_methods(["GET", "POST"])
def crew_logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "Logged out of mission control.")
    return redirect('home')


# --------------------------------------------------------------------------
# API & Backward Compatibility Views
# --------------------------------------------------------------------------

def json_error(message, status=400, errors=None):
    payload = {'status': 'error', 'message': message}
    if errors:
        payload['errors'] = errors
    return JsonResponse(payload, status=status)


def json_success(data=None, message=None, status=200):
    payload = {'status': 'success'}
    if message:
        payload['message'] = message
    if data is not None:
        payload['data'] = data
    return JsonResponse(payload, status=status)


def parse_request_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except Exception:
        return {}


@ensure_csrf_cookie
@require_GET
def get_csrf_token(request):
    token = get_token(request)
    return json_success({'csrftoken': token})


@require_POST
def register_view(request):
    data = parse_request_body(request) or request.POST
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', ''))

    errors = {}
    if not username:
        errors['username'] = 'Username is required.'
    elif len(username) < 3:
        errors['username'] = 'Username must be at least 3 characters long.'
    elif User.objects.filter(username__iexact=username).exists():
        errors['username'] = 'This username is already taken. Please choose another.'

    if not email:
        errors['email'] = 'Email is required.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors['email'] = 'Please enter a valid email address.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 6:
        errors['password'] = 'Password must be at least 6 characters long.'

    if errors:
        return json_error('Registration validation failed.', status=400, errors=errors)

    try:
        user = User.objects.create_user(username=username, email=email, password=password)
        UserProgress.objects.create(user=user)
        login(request, user)
    except Exception as e:
        return json_error(f"Failed to create account: {str(e)}", status=500)

    progress = user.progress
    rank_info = progress.calculate_level_and_rank()

    return json_success({
        'user': {'id': user.id, 'username': user.username},
        'achievements': rank_info,
    }, message='Registration successful!', status=201)


@require_POST
def login_view(request):
    data = parse_request_body(request) or request.POST
    username = str(data.get('username', '')).strip()
    password = str(data.get('password', ''))

    if not username or not password:
        return json_error('Both username and password are required.', status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return json_error('Invalid username or password.', status=401)
    if not user.is_active:
        return json_error('This account is inactive.', status=403)

    login(request, user)
    progress, _ = UserProgress.objects.get_or_create(user=user)
    rank_info = progress.calculate_level_and_rank()

    return json_success({
        'user': {'id': user.id, 'username': user.username},
        'achievements': rank_info,
    }, message='Login successful!')


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        return json_success(message='Logged out successfully.')
    return json_success(message='No active session.')


@require_GET
def current_user_view(request):
    if not request.user.is_authenticated:
        return json_success({'is_authenticated': False, 'user': None})

    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    rank_info = progress.calculate_level_and_rank()

    return json_success({
        'is_authenticated': True,
        'user': {'id': request.user.id, 'username': request.user.username},
        'achievements': rank_info,
        'progress': {
            'total_questions_answered': progress.total_questions_answered,
            'total_correct_answers': progress.total_correct_answers,
            'total_wrong_answers': progress.total_wrong_answers,
            'unique_questions_answered': progress.unique_questions_answered,
            'unique_questions_solved': progress.unique_questions_solved,
            'accuracy_rate': progress.accuracy_rate,
            'last_activity': progress.last_activity.isoformat() if progress.last_activity else None,
        }
    })


@require_GET
def planets_list_view(request):
    cats = Category.objects.filter(is_active=True).prefetch_related('vehicles')
    data = []
    for c in cats:
        data.append({
            'id': c.id,
            'name': c.name,
            'slug': c.slug,
            'kind': c.kind,
            'icon': c.icon,
            'description': c.description,
            'texture_image': c.texture_image,
            'vehicle_count': c.vehicles.count()
        })
    return json_success(data)


@require_GET
def planet_vehicles_view(request, planet_identifier):
    if planet_identifier.isdigit():
        cat = get_object_or_404(Category, id=int(planet_identifier), is_active=True)
    else:
        cat = get_object_or_404(Category, slug=planet_identifier.lower(), is_active=True)

    vehicles = cat.vehicles.filter(is_published=True).prefetch_related('images', 'questions')
    data = []
    for v in vehicles:
        data.append({
            'id': v.id,
            'category': cat.slug,
            'code': v.code,
            'name': v.name,
            'slug': v.slug,
            'tagline': v.tagline,
            'launch_date': v.launch_date.isoformat() if v.launch_date else None,
            'landing_date': v.landing_date.isoformat() if v.landing_date else None,
            'coordinates': v.coordinates,
            'image': v.image_path,
            'questions_count': v.questions.count(),
        })
    return json_success(data)


@require_GET
def vehicle_story_view(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    stories = vehicle.stories.all()
    primary_story = stories.first()

    return json_success({
        'vehicle_id': vehicle.id,
        'vehicle_name': vehicle.name,
        'vehicle_code': vehicle.code,
        'story': primary_story.content if primary_story else '',
        'sections': [
            {'id': s.id, 'title': s.title, 'content': s.content, 'order': s.order}
            for s in stories
        ]
    })


@require_GET
def vehicle_questions_view(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    questions = vehicle.questions.prefetch_related('answers').all()

    data = []
    for q in questions:
        options = [{'id': a.id, 'text': a.text, 'order': a.order} for a in q.answers.all()]
        data.append({
            'id': q.id,
            'vehicle_id': vehicle.id,
            'vehicle_code': vehicle.code,
            'text': q.text,
            'options': options,
            'option_texts': [a.text for a in q.answers.all()]
        })

    return json_success(data)


@require_POST
def submit_answer_view(request, question_id=None):
    data = parse_request_body(request) or request.POST
    q_id = question_id or data.get('question_id')
    vehicle_id = data.get('vehicle_id')

    if not q_id and not vehicle_id:
        return json_error('Missing question_id or vehicle_id.', status=400)

    try:
        questions = Question.objects.select_related('vehicle').prefetch_related('answers')
        if q_id:
            question = questions.get(id=q_id)
        else:
            question = questions.filter(vehicle_id=vehicle_id).order_by('order', 'id').first()
            if question is None:
                return json_error('Question not found.', status=404)
    except (Question.DoesNotExist, ValueError):
        return json_error('Question not found.', status=404)

    answer_id = data.get('answer_id')
    answer_text = str(data.get('answer', data.get('selected_answer', ''))).strip()

    selected_answer = None
    if answer_id:
        selected_answer = question.answers.filter(id=answer_id).first()
    elif answer_text:
        selected_answer = question.answers.filter(text__iexact=answer_text).first()

    if not selected_answer:
        return json_error('Invalid answer choice for this question.', status=400)

    is_correct = selected_answer.is_correct
    correct_ans_obj = question.answers.filter(is_correct=True).first()
    correct_answer_text = correct_ans_obj.text if correct_ans_obj else ''

    user = request.user
    progress_data = None

    if user.is_authenticated:
        with transaction.atomic():
            progress, _ = UserProgress.objects.select_for_update().get_or_create(user=user)
            QuestionAttempt.objects.create(
                user=user,
                question=question,
                selected_answer=selected_answer,
                selected_text=selected_answer.text,
                is_correct=is_correct,
                attempted_at=timezone.now()
            )
            progress.total_questions_answered += 1
            if is_correct:
                progress.total_correct_answers += 1
            else:
                progress.total_wrong_answers += 1
            progress.save()

            rank_info = progress.calculate_level_and_rank()
            progress_data = {
                'total_questions_answered': progress.total_questions_answered,
                'total_correct_answers': progress.total_correct_answers,
                'total_wrong_answers': progress.total_wrong_answers,
                'accuracy_rate': progress.accuracy_rate,
                'achievements': rank_info,
            }

    message = 'Correct! Outstanding space exploration knowledge!' if is_correct else 'Incorrect answer. Keep exploring and try again!'
    return json_success({
        'is_correct': is_correct,
        'correct_answer': correct_answer_text,
        'feedback': message,
        'progress': progress_data,
    }, message=message)


@require_GET
def user_achievements_view(request):
    if not request.user.is_authenticated:
        return json_error('Authentication required to view achievements.', status=401)

    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    rank_info = progress.calculate_level_and_rank()
    solved_count = request.user.certificates.count()
    total_missions = Vehicle.objects.filter(is_published=True).count()

    return json_success({
        'rank': rank_info['rank'],
        'level': rank_info['level'],
        'xp': rank_info['xp'],
        'badges': rank_info['badges'],
        'total_missions': total_missions,
        'solved_missions': solved_count,
        'diploma_unlocked': solved_count >= total_missions and total_missions > 0
    })


@require_GET
def user_progress_view(request):
    if not request.user.is_authenticated:
        return json_error('Authentication required to view progress.', status=401)

    progress, _ = UserProgress.objects.get_or_create(user=request.user)
    solved_vehicle_ids = list(
        request.user.certificates.values_list('vehicle_id', flat=True).distinct()
    )

    return json_success({
        'total_questions_answered': progress.total_questions_answered,
        'total_correct_answers': progress.total_correct_answers,
        'total_wrong_answers': progress.total_wrong_answers,
        'accuracy_rate': progress.accuracy_rate,
        'last_activity': progress.last_activity.isoformat() if progress.last_activity else None,
        'solved_vehicle_ids': solved_vehicle_ids,
    })


@require_GET
def missions_database_view(request):
    """
    Interactive Mission Database & Telemetry Records View.
    Allows searching, category filtering, column sorting, and pagination
    over the imported NASA relational dataset.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('cat', 'all').strip().lower()
    sort_by = request.GET.get('sort', 'order').strip()
    direction = request.GET.get('dir', 'asc').strip().lower()

    vehicles = Vehicle.objects.filter(is_published=True).select_related('category').prefetch_related('specs', 'questions')

    if category_slug and category_slug != 'all':
        vehicles = vehicles.filter(category__slug=category_slug)

    if query:
        vehicles = vehicles.filter(
            models.Q(name__icontains=query) |
            models.Q(code__icontains=query) |
            models.Q(raw_location__icontains=query) |
            models.Q(coordinates__icontains=query) |
            models.Q(notes__icontains=query)
        )

    # Allowed sort fields
    valid_sorts = {
        'name': 'name',
        'code': 'code',
        'launch': 'launch_date',
        'landing': 'landing_date',
        'category': 'category__name',
        'order': 'order',
    }
    field_name = valid_sorts.get(sort_by, 'order')
    if direction == 'desc':
        field_name = '-' + field_name

    vehicles = vehicles.order_by(field_name, 'id')

    # Pagination: up to 24 missions per page so complete datasets render cleanly without artificial cutoff
    paginator = Paginator(vehicles, 24)
    page_num = request.GET.get('page', 1)
    try:
        page_obj = paginator.get_page(page_num)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.get_page(1)

    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    total_count = vehicles.count()

    context = {
        'page_obj': page_obj,
        'vehicles': page_obj.object_list,
        'categories': categories,
        'selected_category': category_slug,
        'query': query,
        'sort_by': sort_by,
        'direction': direction,
        'total_count': total_count,
    }
    return render(request, 'missions/dataset_explorer.html', context)


@require_GET
def data_json_view(request):
    """
    Dynamically generates the canonical data.json structure from the database.
    Ensures full backward compatibility for any external consumers.
    """
    categories = Category.objects.filter(is_active=True).prefetch_related(
        'vehicles__stories',
        'vehicles__questions__answers'
    )

    output = {}
    for cat in categories:
        cat_key = cat.slug.lower()
        output[cat_key] = []

        for v in cat.vehicles.filter(is_published=True):
            story_obj = v.stories.first()
            question_obj = v.questions.first()

            questions_list = []
            for q in v.questions.all().order_by('order', 'id'):
                questions_list.append({
                    "id": q.id,
                    "question": q.text,
                    "options": [a.text for a in q.answers.all().order_by('order', 'id')],
                    "order": q.order
                })

            options = [a.text for a in question_obj.answers.all()] if question_obj else []

            output[cat_key].append({
                "id": v.id,
                "code": v.code,
                "name": v.name,
                "slug": v.slug,
                "tagline": v.tagline,
                "launch_date": v.launch_date.isoformat() if v.launch_date else "",
                "landing_date": v.landing_date.isoformat() if v.landing_date else "",
                "coordinates": v.coordinates,
                "image": v.image_path,
                "story": story_obj.content if story_obj else "",
                "questions": questions_list,
                "question": question_obj.text if question_obj else "",
                "options": options,
            })

    return JsonResponse(output, json_dumps_params={'indent': 2})
