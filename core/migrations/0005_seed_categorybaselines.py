from decimal import Decimal
from django.db import migrations

BASELINES = [
    ('phones',      300,    8000,   2000),
    ('electronics', 200,    12000,  2500),
    ('clothing',    30,     800,    150),
    ('furniture',   300,    6000,   1200),
    ('vehicles',    20000,  250000, 55000),
    ('other',       50,     2000,   350),
]


def seed(apps, schema_editor):
    CategoryBaseline = apps.get_model('core', 'CategoryBaseline')
    for category, mn, mx, typical in BASELINES:
        CategoryBaseline.objects.get_or_create(
            category=category,
            defaults={
                'min_value': Decimal(mn),
                'max_value': Decimal(mx),
                'typical_value': Decimal(typical),
            },
        )


def unseed(apps, schema_editor):
    CategoryBaseline = apps.get_model('core', 'CategoryBaseline')
    CategoryBaseline.objects.filter(category__in=[c for c, *_ in BASELINES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_devicetoken_loginattempt'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
