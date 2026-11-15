from django.db import migrations
from django.utils.text import slugify

from missions.seed_data import CATEGORY_META, VEHICLE_META


def forwards(apps, schema_editor):
    Category = apps.get_model('missions', 'Category')
    Vehicle = apps.get_model('missions', 'Vehicle')
    VehicleSpec = apps.get_model('missions', 'VehicleSpec')
    Story = apps.get_model('missions', 'Story')

    for slug, meta in CATEGORY_META.items():
        Category.objects.filter(slug=slug).update(**meta)

    used = set()
    for v in Vehicle.objects.all().order_by('id'):
        meta = VEHICLE_META.get(v.id, {})
        base = meta.get('slug') or slugify(v.name)[:70] or f'vehicle-{v.id}'
        slug, n = base, 2
        while slug in used or Vehicle.objects.filter(slug=slug).exclude(pk=v.pk).exists():
            slug, n = f'{base}-{n}', n + 1
        used.add(slug)
        v.slug = slug
        for field in ('tagline', 'mission_type', 'status_label', 'milestone_label', 'location_label'):
            if field in meta:
                setattr(v, field, meta[field])
        v.save()
        if meta.get('specs') and not VehicleSpec.objects.filter(vehicle=v).exists():
            VehicleSpec.objects.bulk_create(
                [VehicleSpec(vehicle=v, label=l, value=val, order=i) for i, (l, val) in enumerate(meta['specs'])])
        if meta.get('story'):
            Story.objects.filter(vehicle=v, order=0).update(content=meta['story'])


class Migration(migrations.Migration):
    dependencies = [('missions', '0003_overhaul_schema')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
