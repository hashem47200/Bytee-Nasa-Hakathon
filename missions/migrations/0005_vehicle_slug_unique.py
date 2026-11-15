from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('missions', '0004_seed_overhaul_data')]
    operations = [
        migrations.AlterField(model_name='vehicle', name='slug', field=models.SlugField(
            max_length=80, unique=True, help_text='Used in the URL: /vehicle/<slug>/')),
    ]
