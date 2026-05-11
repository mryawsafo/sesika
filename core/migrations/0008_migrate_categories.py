from django.db import migrations

CATEGORY_MAP = {
    'phones': 'phones_tablets',
    'clothing': 'fashion',
    'furniture': 'home_furniture',
}

DEFAULT_SUBCATEGORY = {
    'phones_tablets': 'other_android',
    'computers': 'laptops',
    'electronics': 'other_electronics',
    'gaming': 'consoles',
    'vehicles': 'cars',
    'fashion': 'mens_fashion',
    'home_furniture': 'furniture',
    'health_beauty': 'health',
    'sports_hobbies': 'sports',
    'tools_equipment': 'tools',
    'other': 'other_items',
}

CATEGORY_BASELINES = {
    'phones_tablets': {'min': 500,   'typical': 1500,  'max': 8000},
    'computers':      {'min': 800,   'typical': 2500,  'max': 12000},
    'electronics':    {'min': 200,   'typical': 1500,  'max': 8000},
    'gaming':         {'min': 300,   'typical': 1200,  'max': 5000},
    'vehicles':       {'min': 15000, 'typical': 45000, 'max': 200000},
    'fashion':        {'min': 50,    'typical': 150,   'max': 1500},
    'home_furniture': {'min': 200,   'typical': 800,   'max': 8000},
    'health_beauty':  {'min': 50,    'typical': 200,   'max': 2000},
    'sports_hobbies': {'min': 100,   'typical': 400,   'max': 3000},
    'tools_equipment':{'min': 150,   'typical': 600,   'max': 5000},
    'other':          {'min': 50,    'typical': 200,   'max': 2000},
}


def migrate_forward(apps, schema_editor):
    Listing = apps.get_model('core', 'Listing')
    CategoryBaseline = apps.get_model('core', 'CategoryBaseline')

    for listing in Listing.objects.all():
        new_cat = CATEGORY_MAP.get(listing.category, listing.category)
        listing.category = new_cat
        listing.subcategory = DEFAULT_SUBCATEGORY.get(new_cat, 'other_items')
        listing.save(update_fields=['category', 'subcategory'])

    for old_cat, new_cat in CATEGORY_MAP.items():
        CategoryBaseline.objects.filter(category=old_cat).update(category=new_cat)

    for category, vals in CATEGORY_BASELINES.items():
        CategoryBaseline.objects.update_or_create(
            category=category,
            defaults={
                'min_value': vals['min'],
                'typical_value': vals['typical'],
                'max_value': vals['max'],
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_marketprice_subcategory'),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrations.RunPython.noop),
    ]
