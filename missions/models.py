import secrets
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from django.conf import settings

User = get_user_model()


def _new_certificate_code():
    """Generates an official NASA explorer certificate code e.g. NASA-7A9B3F."""
    return f"NASA-{secrets.token_hex(4).upper()}"


def pass_percent():
    """Returns the passing mark percentage for mission exams (default 60%)."""
    return getattr(settings, 'NASA_PASS_PERCENT', 60)


class Category(models.Model):
    """
    Mission operational domain (e.g., Mars, Moon, Space).
    Separates planetary surfaces from deep space observatories & probes.
    """
    CATEGORY_KINDS = [
        ('planetary', 'Planetary surface (landers, rovers, crewed modules)'),
        ('deep_space', 'Deep space (observatories, probes, interstellar)'),
    ]

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True, db_index=True)
    kind = models.CharField(max_length=20, choices=CATEGORY_KINDS, default='planetary')
    icon = models.CharField(max_length=8, blank=True, default='🪐', help_text='One emoji shown on the toggle bar.')
    description = models.TextField(blank=True, default='')
    texture_image = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Path under static/, e.g. images/planets/mars-texture.jpg'
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return f"{self.icon} {self.name}"

    @property
    def is_deep_space(self):
        return self.kind == 'deep_space' or self.slug == 'space'


# Backward compatibility alias
Planet = Category


class Vehicle(models.Model):
    """
    Spacecraft, rover, lander, observatory or probe.
    Modular structure supporting planetary surfaces and deep space trajectories.
    """
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='vehicles', db_index=True)
    code = models.CharField(max_length=30, db_index=True)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80, unique=True, help_text='Used in the URL: /vehicle/<slug>/')
    tagline = models.CharField(max_length=200, blank=True, default='')
    mission_type = models.CharField(max_length=80, blank=True, default='')
    status_label = models.CharField(max_length=80, blank=True, default='')
    launch_date = models.DateField(null=True, blank=True)
    landing_date = models.DateField(
        null=True, blank=True,
        help_text='Landing, orbit arrival or other headline milestone date.'
    )
    milestone_label = models.CharField(
        max_length=60, default='Landing date',
        help_text="Label for the date above, e.g. 'Arrived at L2'."
    )
    coordinates = models.CharField(max_length=100, blank=True, default='')
    surface_lat = models.FloatField(null=True, blank=True, help_text="Latitude on planetary surface (-90 to +90)")
    surface_lon = models.FloatField(null=True, blank=True, help_text="Longitude on planetary surface (-180 to +180)")
    raw_location = models.CharField(max_length=255, blank=True, default='', help_text="Raw location text from Excel dataset")
    raw_launch_text = models.CharField(max_length=150, blank=True, default='', help_text="Exact launch date string from Excel")
    raw_landing_text = models.CharField(max_length=255, blank=True, default='', help_text="Exact landing/arrival string from Excel")
    notes = models.TextField(blank=True, default='', help_text="Astronomical, orbital, or mission notes from dataset")
    location_label = models.CharField(
        max_length=40, default='Landing site',
        help_text="Label for coordinates, e.g. 'Position' for deep-space craft."
    )
    image_path = models.CharField(max_length=255, blank=True, default='')
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category__order', 'order', 'id']
        verbose_name = 'Vehicle'
        verbose_name_plural = 'Vehicles'

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_absolute_url(self):
        return reverse('vehicle_detail', kwargs={'slug': self.slug})

    def get_quiz_url(self):
        return reverse('vehicle_quiz', kwargs={'slug': self.slug})

    @property
    def question_total(self):
        return self.questions.count()

    @property
    def planet(self):
        return self.category


class VehicleSpec(models.Model):
    """
    Key technical specs for editorial presentation on the vehicle detail page.
    """
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='specs')
    label = models.CharField(max_length=80)
    value = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Spec'
        verbose_name_plural = 'Specs'

    def __str__(self):
        return f"{self.vehicle.code}: {self.label} = {self.value}"


class VehicleImage(models.Model):
    """
    Photographic and telemetry images of the vehicle.
    """
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='images')
    image_path = models.CharField(max_length=255)
    caption = models.CharField(max_length=255, blank=True, default='')
    is_primary = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'id']
        verbose_name = 'Vehicle Image'
        verbose_name_plural = 'Vehicle Images'
        constraints = [
            models.UniqueConstraint(fields=['vehicle', 'image_path'], name='uniq_vehicle_image_path'),
        ]

    def __str__(self):
        return f"Image for {self.vehicle.name} ({self.image_path})"


class Story(models.Model):
    """
    Educational mission narrative told from the perspective of the spacecraft.
    """
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='stories')
    title = models.CharField(max_length=200, blank=True, default='')
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Story'
        verbose_name_plural = 'Stories'

    def __str__(self):
        return f"Story for {self.vehicle.name} (Section {self.order + 1})"


class Question(models.Model):
    """
    Knowledge check question associated with a mission vehicle.
    """
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    hint = models.TextField(blank=True, default='', help_text='Shown after a wrong answer.')
    explanation = models.TextField(blank=True, default='', help_text='Optional: shown in the answer review after passing.')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"Q({self.vehicle.code}): {self.text[:60]}"


class Answer(models.Model):
    """
    Answer choice for a knowledge-check question.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Answer Choice'
        verbose_name_plural = 'Answer Choices'
        constraints = [
            models.UniqueConstraint(fields=['question', 'text'], name='uniq_answer_question_text'),
        ]

    def __str__(self):
        status = " [CORRECT]" if self.is_correct else ""
        return f"{self.text}{status}"


class QuizAttempt(models.Model):
    """
    Full mission exam attempt recorded on submission.
    Calculates passing status using the 60% threshold.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='quiz_attempts')
    total_questions = models.PositiveIntegerField()
    correct_count = models.PositiveIntegerField()
    score_percent = models.PositiveSmallIntegerField()
    pass_percent = models.PositiveSmallIntegerField(help_text='Threshold in force when the exam was taken.')
    passed = models.BooleanField(db_index=True)
    answers = models.JSONField(blank=True, default=dict, help_text='{question_id: answer_id}')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Exam Attempt'
        verbose_name_plural = 'Exam Attempts'

    def __str__(self):
        status = "PASSED" if self.passed else "FAILED"
        return f"{self.user.username} - {self.vehicle.name} ({self.score_percent}%) [{status}]"


class Certificate(models.Model):
    """
    Personalized NASA Explorer Certificate unlocked upon scoring >= 60%.
    """
    code = models.CharField(max_length=20, unique=True, default=_new_certificate_code, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='certificates')
    recipient_name = models.CharField(max_length=80)
    score_percent = models.PositiveSmallIntegerField()
    issued_at = models.DateTimeField(default=timezone.now)
    quiz_attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='certificates'
    )

    class Meta:
        ordering = ['-issued_at']
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'
        constraints = [
            models.UniqueConstraint(fields=['user', 'vehicle'], name='uniq_user_vehicle_certificate'),
        ]

    def __str__(self):
        return f"Certificate {self.code} - {self.recipient_name} ({self.vehicle.name})"

    def get_absolute_url(self):
        return f"{reverse('certificate')}?mission={self.vehicle.slug}"


class UserProgress(models.Model):
    """
    Aggregate progress and achievement metrics for an authenticated user.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='progress')
    total_questions_answered = models.PositiveIntegerField(default=0)
    total_correct_answers = models.PositiveIntegerField(default=0)
    total_wrong_answers = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Progress'
        verbose_name_plural = 'User Progress Records'

    def __str__(self):
        return f"{self.user.username} Progress ({self.total_correct_answers} correct / {self.total_questions_answered} attempts)"

    @property
    def unique_questions_answered(self):
        return self.user.question_attempts.values('question_id').distinct().count()

    @property
    def unique_questions_solved(self):
        return self.user.question_attempts.filter(is_correct=True).values('question_id').distinct().count()

    @property
    def accuracy_rate(self):
        if self.total_questions_answered == 0:
            return 0.0
        return round((self.total_correct_answers / self.total_questions_answered) * 100, 1)

    def calculate_level_and_rank(self):
        solved_count = self.user.certificates.count()
        ranks = [
            'CADET',
            'TRAINEE',
            'ROVER OPERATOR',
            'MISSION SPECIALIST',
            'FLIGHT COMMANDER',
            'MISSION DIRECTOR',
            'EXPLORER LEGEND'
        ]
        rank_index = min(solved_count, len(ranks) - 1)
        xp = solved_count * 250
        return {
            'rank': ranks[rank_index],
            'level': rank_index,
            'xp': xp,
            'badges': solved_count,
        }


class QuestionAttempt(models.Model):
    """
    Record of an individual question attempt submitted by an authenticated user.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    selected_answer = models.ForeignKey(Answer, on_delete=models.SET_NULL, null=True, blank=True, related_name='attempts')
    selected_text = models.CharField(max_length=255)
    is_correct = models.BooleanField()
    attempted_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-attempted_at']
        verbose_name = 'Question Attempt'
        verbose_name_plural = 'Question Attempts'
        indexes = [
            models.Index(fields=['user', 'question']),
            models.Index(fields=['user', 'attempted_at']),
        ]

    def __str__(self):
        status = "CORRECT" if self.is_correct else "WRONG"
        return f"{self.user.username} -> Q{self.question_id}: {status} at {self.attempted_at}"
