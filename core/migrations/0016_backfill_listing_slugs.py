from django.db import migrations, models
from django.utils.text import slugify


def backfill_slugs(apps, schema_editor):
    Listing = apps.get_model('core', 'Listing')
    for listing in Listing.objects.filter(slug__isnull=True):
        listing.slug = f"{slugify(listing.title)[:200]}-{listing.pk}"
        listing.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_seed_categories'),
    ]

    operations = [
        migrations.RunPython(backfill_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='listing',
            name='slug',
            field=models.SlugField(blank=True, max_length=230, unique=True),
        ),
    ]
