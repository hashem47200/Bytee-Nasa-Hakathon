from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import missions.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('missions', '0002_unique_constraints'),
    ]

    operations = [
        # Planet -> Category
        migrations.RenameModel(old_name='Planet', new_name='Category'),
        migrations.RenameField(model_name='vehicle', old_name='planet', new_name='category'),
        migrations.AlterModelOptions(
            name='category',
            options={'ordering': ['order', 'name'], 'verbose_name': 'Category', 'verbose_name_plural': 'Categories'},
        ),
        migrations.AddField(model_name='category', name='kind', field=models.CharField(
            choices=[('planetary', 'Planetary surface (landers, rovers, crewed modules)'),
                     ('deep_space', 'Deep space (observatories, probes, interstellar)')],
            default='planetary', max_length=20)),
        migrations.AddField(model_name='category', name='icon', field=models.CharField(
            blank=True, default='🪐', help_text='One emoji shown on the toggle bar.', max_length=8)),
        migrations.AddField(model_name='category', name='order', field=models.PositiveIntegerField(default=0)),
        migrations.AlterField(model_name='category', name='texture_image', field=models.CharField(
            blank=True, default='', help_text='Path under static/, e.g. images/planets/mars-texture.jpg', max_length=255)),

        # Vehicle
        migrations.AlterField(model_name='vehicle', name='id', field=models.AutoField(primary_key=True, serialize=False)),
        migrations.AddField(model_name='vehicle', name='slug', field=models.SlugField(
            max_length=80, null=True, blank=True, help_text='Used in the URL: /vehicle/<slug>/')),
        migrations.AddField(model_name='vehicle', name='tagline', field=models.CharField(blank=True, default='', max_length=200)),
        migrations.AddField(model_name='vehicle', name='mission_type', field=models.CharField(blank=True, default='', max_length=80)),
        migrations.AddField(model_name='vehicle', name='status_label', field=models.CharField(blank=True, default='', max_length=80)),
        migrations.AddField(model_name='vehicle', name='milestone_label', field=models.CharField(
            default='Landing date', help_text="Label for the date above, e.g. 'Arrived at L2'.", max_length=60)),
        migrations.AddField(model_name='vehicle', name='location_label', field=models.CharField(
            default='Landing site', help_text="Label for coordinates, e.g. 'Position' for deep-space craft.", max_length=40)),
        migrations.AddField(model_name='vehicle', name='is_published', field=models.BooleanField(default=True)),
        migrations.AlterModelOptions(
            name='vehicle',
            options={'ordering': ['category__order', 'order', 'id'], 'verbose_name': 'Vehicle', 'verbose_name_plural': 'Vehicles'},
        ),
        migrations.AlterField(model_name='vehicle', name='landing_date', field=models.DateField(
            blank=True, null=True, help_text='Landing, orbit arrival or other headline milestone date.')),

        # Questions: allow any number per vehicle without order collisions
        migrations.RemoveConstraint(model_name='question', name='uniq_question_vehicle_order'),
        migrations.RemoveConstraint(model_name='story', name='uniq_story_vehicle_order'),
        migrations.AddField(model_name='question', name='hint', field=models.TextField(
            blank=True, default='', help_text='Shown after a wrong answer.')),
        migrations.AddField(model_name='question', name='explanation', field=models.TextField(
            blank=True, default='', help_text='Optional: shown in the answer review after passing.')),

        # New models
        migrations.CreateModel(
            name='VehicleSpec',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=80)),
                ('value', models.CharField(max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='specs', to='missions.vehicle')),
            ],
            options={'verbose_name': 'Spec', 'verbose_name_plural': 'Specs', 'ordering': ['order', 'id']},
        ),
        migrations.CreateModel(
            name='QuizAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_questions', models.PositiveIntegerField()),
                ('correct_count', models.PositiveIntegerField()),
                ('score_percent', models.PositiveSmallIntegerField()),
                ('pass_percent', models.PositiveSmallIntegerField(help_text='Threshold in force when the exam was taken.')),
                ('passed', models.BooleanField(db_index=True)),
                ('answers', models.JSONField(blank=True, default=dict, help_text='{question_id: answer_id}')),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_attempts', to=settings.AUTH_USER_MODEL)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_attempts', to='missions.vehicle')),
            ],
            options={'verbose_name': 'Exam Attempt', 'verbose_name_plural': 'Exam Attempts', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Certificate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(default=missions.models._new_certificate_code, editable=False, max_length=20, unique=True)),
                ('recipient_name', models.CharField(max_length=80)),
                ('score_percent', models.PositiveSmallIntegerField()),
                ('issued_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('quiz_attempt', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='certificates', to='missions.quizattempt')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to=settings.AUTH_USER_MODEL)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to='missions.vehicle')),
            ],
            options={'verbose_name': 'Certificate', 'verbose_name_plural': 'Certificates', 'ordering': ['-issued_at']},
        ),
        migrations.AddConstraint(
            model_name='certificate',
            constraint=models.UniqueConstraint(fields=('user', 'vehicle'), name='uniq_certificate_user_vehicle'),
        ),
    ]
