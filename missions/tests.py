import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import escape

from missions.models import Category, Vehicle, Question, Answer, QuizAttempt, Certificate, UserProgress, pass_percent
from missions.services import grade, record_attempt, calculate_user_celestial_progress

User = get_user_model()


class ByteeRestorationAndIntegrityTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed test database with authentic importer
        from scripts.import_nasa import run_import
        run_import()

        self.user = User.objects.create_user(
            username='CommanderBytee',
            email='commander@bytee.space',
            password='SafePassword123'
        )
        self.progress, _ = UserProgress.objects.get_or_create(user=self.user)

    def test_authentic_dataset_integrity(self):
        """Database must strictly contain the 13 authentic vehicles from nasa_data.xlsx."""
        self.assertEqual(Vehicle.objects.count(), 13)

        # 2 Categories only: Mars and Moon
        cats = list(Category.objects.values_list('slug', flat=True))
        self.assertIn('mars', cats)
        self.assertIn('moon', cats)
        self.assertNotIn('space', cats)

        # 4 Moon missions (all surface)
        moon_vehicles = Vehicle.objects.filter(category__slug='moon')
        self.assertEqual(moon_vehicles.count(), 4)
        for v in moon_vehicles:
            self.assertFalse(v.is_nearby_space)

        # 9 Mars missions (5 surface, 4 nearby-space)
        mars_vehicles = Vehicle.objects.filter(category__slug='mars')
        self.assertEqual(mars_vehicles.count(), 9)
        self.assertEqual(mars_vehicles.filter(is_nearby_space=False).count(), 5)
        self.assertEqual(mars_vehicles.filter(is_nearby_space=True).count(), 4)

        # Zero synthetic craft
        synthetic_slugs = [
            'james-webb-space-telescope', 'hubble-space-telescope',
            'voyager-1', 'voyager-2', 'parker-solar-probe'
        ]
        for slug in synthetic_slugs:
            self.assertFalse(
                Vehicle.objects.filter(slug=slug).exists(),
                f"Synthetic craft {slug} should have been purged from database."
            )

    def test_strict_100_percent_pass_requirement(self):
        """Pass mark must be 100%. Any score below 100% must fail and not count."""
        self.assertEqual(pass_percent(), 100)
        v = Vehicle.objects.filter(category__slug='moon').first()
        questions = list(v.questions.prefetch_related('answers').all())
        self.assertGreaterEqual(len(questions), 2)

        # 1 correct, 1 wrong -> 50% score
        q1 = questions[0]
        q2 = questions[1]
        correct_ans = q1.answers.filter(is_correct=True).first()
        wrong_ans = q2.answers.filter(is_correct=False).first()

        selections = {q1.id: correct_ans.id, q2.id: wrong_ans.id}
        result = grade(v, selections)
        self.assertEqual(result.percent, 50)
        self.assertFalse(result.passed)

        attempt, cert = record_attempt(self.user, v, result)
        self.assertFalse(attempt.passed)
        self.assertIsNone(cert)

    def test_100_percent_full_mark_advances_progress(self):
        """100% full-mark exam advances celestial progress."""
        v = Vehicle.objects.filter(category__slug='moon').first()
        questions = list(v.questions.prefetch_related('answers').all())

        selections = {
            q.id: q.answers.filter(is_correct=True).first().id
            for q in questions
        }
        result = grade(v, selections)
        self.assertEqual(result.percent, 100)
        self.assertTrue(result.passed)

        attempt, cert = record_attempt(self.user, v, result)
        self.assertTrue(attempt.passed)

        # Check celestial progress (1 of 4 Moon vehicles = 25%)
        stats = calculate_user_celestial_progress(self.user)
        self.assertEqual(stats['moon_passed'], 1)
        self.assertEqual(stats['moon_total'], 4)
        self.assertEqual(stats['moon_percent'], 25)
        self.assertEqual(stats['mars_percent'], 0)  # Mars remains independent

    def test_moon_certificate_unlocks_at_100_percent_completion(self):
        """Moon Certificate of Exploration is issued when all 4 Moon vehicle exams achieve 100%."""
        moon_vehicles = list(Vehicle.objects.filter(category__slug='moon'))
        self.assertEqual(len(moon_vehicles), 4)

        for v in moon_vehicles:
            questions = list(v.questions.prefetch_related('answers').all())
            selections = {q.id: q.answers.filter(is_correct=True).first().id for q in questions}
            res = grade(v, selections)
            record_attempt(self.user, v, res)

        stats = calculate_user_celestial_progress(self.user)
        self.assertEqual(stats['moon_percent'], 100)
        self.assertTrue(stats['moon_certified'])

        # Certificate created in DB
        cert = Certificate.objects.filter(user=self.user, body_name='Moon').first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.title, 'Moon Certificate of Exploration')
        self.assertEqual(cert.score_percent, 100)

    def test_home_page_renders_bytee_3d_hub(self):
        """Home page must render 3D controls, dual progress bars, and zero flat cards grid."""
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bytee")
        self.assertContains(resp, "Mars Exploration Progress")
        self.assertContains(resp, "Moon Exploration Progress")
        self.assertContains(resp, "planet-canvas-container")
        self.assertContains(resp, "vehicle-modal")
        # Ensure old flat card grid is removed
        self.assertNotContains(resp, "missions-grid")

    def test_relational_database_view_shows_13_records(self):
        """Relational database table view must show exactly 13 records with Bytee branding."""
        resp = self.client.get(reverse('dataset_explorer'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bytee")
        self.assertContains(resp, "13 total records")
        self.assertNotContains(resp, "18 total records")
        self.assertNotContains(resp, "Voyager 1")
        self.assertNotContains(resp, "Parker Solar Probe")

    def test_certificate_page_rendering(self):
        """Certificate page must render Mars and Moon celestial credentials without individual vehicle cards."""
        self.client.force_login(self.user)
        resp = self.client.get(reverse('certificate'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bytee")
        self.assertContains(resp, "Mars Certificate")
        self.assertContains(resp, "Moon Certificate")
        self.assertNotContains(resp, "missions certified")
