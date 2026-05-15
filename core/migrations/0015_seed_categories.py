from django.db import migrations


CATEGORIES = [
    ('phones_tablets', 'Phones & Tablets', '📱', 0),
    ('computers', 'Computers & Laptops', '💻', 1),
    ('electronics', 'Electronics', '🔌', 2),
    ('gaming', 'Gaming', '🎮', 3),
    ('vehicles', 'Vehicles', '🚗', 4),
    ('fashion', 'Fashion', '👗', 5),
    ('home_furniture', 'Home & Furniture', '🛋️', 6),
    ('health_beauty', 'Health & Beauty', '💄', 7),
    ('sports_hobbies', 'Sports & Hobbies', '⚽', 8),
    ('tools_equipment', 'Tools & Equipment', '🔧', 9),
    ('handmade_crafts', 'Handmade & Crafts', '🧶', 10),
    ('art_creative', 'Art & Creative', '🎨', 11),
    ('food_plants', 'Food, Plants & Nature', '🌿', 12),
    ('services', 'Services & Commissions', '🛠️', 13),
    ('other', 'Other', '📦', 14),
]

SUBCATEGORIES = {
    'phones_tablets': [
        ('iphones', 'iPhones', 0),
        ('samsung', 'Samsung', 1),
        ('tecno_itel', 'Tecno / Itel', 2),
        ('other_android', 'Other Android', 3),
        ('tablets', 'Tablets', 4),
        ('phone_accessories', 'Accessories', 5),
    ],
    'computers': [
        ('laptops', 'Laptops', 0),
        ('desktops', 'Desktops', 1),
        ('computer_accessories', 'Accessories', 2),
    ],
    'electronics': [
        ('tvs', 'TVs & Displays', 0),
        ('audio', 'Audio & Speakers', 1),
        ('cameras', 'Cameras & Photography', 2),
        ('smart_watches', 'Smart Watches', 3),
        ('other_electronics', 'Other Electronics', 4),
    ],
    'gaming': [
        ('consoles', 'Consoles', 0),
        ('games', 'Games', 1),
        ('gaming_accessories', 'Accessories', 2),
        ('pc_parts', 'PC Parts & GPUs', 3),
    ],
    'vehicles': [
        ('cars', 'Cars', 0),
        ('motorcycles', 'Motorcycles & Scooters', 1),
        ('trucks', 'Trucks & Commercial', 2),
        ('vans', 'Vans / Utility Vehicles', 3),
        ('buses', 'Buses & Minibuses', 4),
        ('taxis', 'Taxis & Ride Share', 5),
        ('boats', 'Boats & Watercraft', 6),
    ],
    'fashion': [
        ('mens_fashion', "Men's Fashion", 0),
        ('womens_fashion', "Women's Fashion", 1),
        ('kids_fashion', "Kids' Fashion", 2),
        ('shoes', 'Shoes', 3),
        ('bags_accessories', 'Bags & Accessories', 4),
        ('sneakers', 'Sneakers', 5),
        ('thrift', 'Thrift & Secondhand', 6),
    ],
    'home_furniture': [
        ('furniture', 'Furniture', 0),
        ('home_appliances', 'Home Appliances', 1),
        ('kitchen', 'Kitchen & Dining', 2),
        ('decor', 'Décor & Accessories', 3),
    ],
    'health_beauty': [
        ('health', 'Health & Medical', 0),
        ('beauty_skincare', 'Beauty & Skincare', 1),
        ('fitness', 'Fitness Equipment', 2),
    ],
    'sports_hobbies': [
        ('sports', 'Sports Equipment', 0),
        ('hobbies_art', 'Hobbies & Art', 1),
        ('musical_instruments', 'Musical Instruments', 2),
    ],
    'tools_equipment': [
        ('tools', 'Tools & DIY', 0),
        ('office_equipment', 'Office Equipment', 1),
        ('industrial', 'Industrial & Commercial', 2),
    ],
    'handmade_crafts': [
        ('crochet_knitting', 'Crochet & Knitting', 0),
        ('woodwork', 'Woodwork', 1),
        ('resin_art', 'Resin Art', 2),
        ('candles_soaps', 'Candles & Soaps', 3),
        ('jewellery', 'Jewellery', 4),
        ('other_handmade', 'Other Handmade', 5),
    ],
    'art_creative': [
        ('paintings', 'Paintings & Drawings', 0),
        ('sculptures', 'Sculptures', 1),
        ('photography', 'Photography', 2),
        ('digital_art', 'Digital Art', 3),
        ('music', 'Music & Recordings', 4),
        ('other_art', 'Other Art', 5),
    ],
    'food_plants': [
        ('potted_plants', 'Potted Plants', 0),
        ('dwarf_trees', 'Dwarf Trees & Bonsai', 1),
        ('flowers', 'Flowers', 2),
        ('food_produce', 'Food & Produce', 3),
        ('seeds_seedlings', 'Seeds & Seedlings', 4),
    ],
    'services': [
        ('graphic_design', 'Graphic Design', 0),
        ('photography_service', 'Photography Service', 1),
        ('tailoring', 'Tailoring & Sewing', 2),
        ('repairs', 'Repairs & Maintenance', 3),
        ('tutoring', 'Tutoring & Training', 4),
        ('creative_commission', 'Creative Commission', 5),
        ('other_service', 'Other Service', 6),
    ],
    'other': [
        ('other_items', 'Other Items', 0),
    ],
}


def seed_categories(apps, schema_editor):
    Category = apps.get_model('core', 'Category')
    Subcategory = apps.get_model('core', 'Subcategory')
    for slug, label, icon, order in CATEGORIES:
        cat = Category.objects.create(slug=slug, label=label, icon=icon, display_order=order)
        for sub_slug, sub_label, sub_order in SUBCATEGORIES.get(slug, []):
            Subcategory.objects.create(
                category=cat,
                slug=sub_slug,
                label=sub_label,
                display_order=sub_order,
            )


def unseed_categories(apps, schema_editor):
    Category = apps.get_model('core', 'Category')
    Category.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_category_listing_attributes_listing_seo_description_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
