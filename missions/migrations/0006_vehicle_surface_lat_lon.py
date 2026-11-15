from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0005_vehicle_slug_unique'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='surface_lat',
            field=models.FloatField(blank=True, help_text='Latitude on planetary surface in degrees (-90 to +90).', null=True),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='surface_lon',
            field=models.FloatField(blank=True, help_text='Longitude on planetary surface in degrees (-180 to +180).', null=True),
        ),
    ]
