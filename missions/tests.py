import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils.html import escape

from missions.models import Category, Vehicle, Question, Answer, QuizAttempt, Certificate, UserProgress
from missions.services import grade, record_attempt

User = get_user_model()


class NASAExplorerHubOverhaulTests(TestCase):
    def setUp(self):
        self.client = Client()
        call_command('import_excel_data')
        self.user = User.objects.create_user(
            username='ExplorerOne',
            email='explorer@nasa.gov',
            password='SafePassword123'
        )
        UserProgress.objects.create(user=self.user)

    def test_categories_and_deep_space_distinction(self):
        """Mars and Moon must be planetary; Space must be framed as deep space without surfaces."""
        cats = {c.slug: c for c in Category.objects.all()}
        self.assertIn('mars', cats)
        self.assertIn('moon', cats)
        self.assertIn('space', cats)

        self.assertFalse(cats['mars'].is_deep_space)
        self.assertFalse(cats['moon'].is_deep_space)
        self.assertTrue(cats['space'].is_deep_space)
        self.assertEqual(cats['space'].kind, 'deep_space')

        # Deep space vehicles
        space_vehicles = cats['space'].vehicles.all()
        self.assertTrue(space_vehicles.filter(slug='james-webb-space-telescope').exists())
        self.assertTrue(space_vehicles.filter(slug='voyager-1').exists())
        self.assertTrue(space_vehicles.filter(slug='parker-solar-probe').exists())
        self.assertTrue(space_vehicles.filter(slug='kepler-space-telescope').exists())
        self.assertTrue(space_vehicles.filter(slug='dawn-mission').exists())

    def test_every_vehicle_has_two_dynamic_questions(self):
        """Every vehicle must have exactly 2 dynamically extensible questions."""
        for v in Vehicle.objects.filter(is_published=True):
            self.assertEqual(
                v.questions.count(), 2,
                f"Vehicle {v.name} ({v.slug}) has {v.questions.count()} questions instead of 2."
            )
            for q in v.questions.all():
                self.assertGreaterEqual(q.answers.count(), 2)
                self.assertTrue(q.answers.filter(is_correct=True).exists())

    def test_home_page_rendering(self):
        """Home page must render with categories, stats, and shareable toggle bar."""
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mission")
        self.assertContains(resp, "Control")
        self.assertContains(resp, "Hub")
        self.assertContains(resp, "Mars")
        self.assertContains(resp, "Moon")
        self.assertContains(resp, "Space")

    def test_vehicle_editorial_page(self):
        """Vehicle story page must render specs, narrative, and 'Launch Mission Exam 🚀' CTA."""
        v = Vehicle.objects.get(slug='apollo-11-eagle')
        resp = self.client.get(reverse('vehicle_detail', kwargs={'slug': v.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Launch Mission Exam")
        self.assertContains(resp, escape(v.name))

    def test_quiz_exam_threshold_60_percent_fail(self):
        """Scoring below 60% must display telemetry failure message and 'Retake Exam' button."""
        v = Vehicle.objects.get(slug='apollo-11-eagle')
        self.client.force_login(self.user)
        questions = list(v.questions.prefetch_related('answers').all().order_by('order', 'id'))

        # Select wrong answers -> 0%
        wrong_data = {}
        for q in questions:
            wrong_ans = q.answers.filter(is_correct=False).first()
            wrong_data[f'q_{q.id}'] = wrong_ans.id

        resp = self.client.post(reverse('vehicle_quiz', kwargs={'slug': v.slug}), data=wrong_data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "TELEMETRY LOST")
        self.assertContains(resp, "Retake Exam")

        # Certificate must NOT be issued
        self.assertFalse(Certificate.objects.filter(user=self.user, vehicle=v).exists())

    def test_quiz_exam_threshold_60_percent_pass_and_certificate(self):
        """Scoring >= 60% must unlock mission success badge and issue personalized certificate."""
        v = Vehicle.objects.get(slug='apollo-11-eagle')
        self.client.force_login(self.user)
        questions = list(v.questions.prefetch_related('answers').all().order_by('order', 'id'))

        # Select correct answers -> 100%
        correct_data = {}
        for q in questions:
            corr_ans = q.answers.filter(is_correct=True).first()
            correct_data[f'q_{q.id}'] = corr_ans.id

        resp = self.client.post(reverse('vehicle_quiz', kwargs={'slug': v.slug}), data=correct_data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "MISSION SUCCESS")

        # Certificate must be created
        cert = Certificate.objects.filter(user=self.user, vehicle=v).first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.score_percent, 100)

        # PDF download must stream valid PDF
        pdf_resp = self.client.get(reverse('certificate_download', kwargs={'code': cert.code}))
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp['Content-Type'], 'application/pdf')
        self.assertTrue(pdf_resp.content.startswith(b'%PDF'))
