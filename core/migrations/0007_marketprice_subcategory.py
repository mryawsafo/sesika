import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_listing_review'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_key', models.CharField(max_length=200, unique=True)),
                ('category', models.CharField(max_length=50)),
                ('subcategory', models.CharField(blank=True, max_length=50)),
                ('price_ghs', models.DecimalField(decimal_places=2, max_digits=10)),
                ('source', models.CharField(default='jiji', max_length=20)),
                ('sample_count', models.PositiveIntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['item_key'],
            },
        ),
        migrations.AddField(
            model_name='listing',
            name='subcategory',
            field=models.CharField(
                blank=True,
                choices=[
                    ('iphones', 'iPhones'), ('samsung', 'Samsung'),
                    ('tecno_itel', 'Tecno / Itel'), ('other_android', 'Other Android'),
                    ('tablets', 'Tablets'), ('phone_accessories', 'Accessories'),
                    ('laptops', 'Laptops'), ('desktops', 'Desktops'),
                    ('computer_accessories', 'Accessories'),
                    ('tvs', 'TVs & Displays'), ('audio', 'Audio & Speakers'),
                    ('cameras', 'Cameras & Photography'), ('smart_watches', 'Smart Watches'),
                    ('other_electronics', 'Other Electronics'),
                    ('consoles', 'Consoles'), ('games', 'Games'),
                    ('gaming_accessories', 'Accessories'),
                    ('cars', 'Cars'), ('motorcycles', 'Motorcycles & Scooters'),
                    ('trucks', 'Trucks & Commercial'),
                    ('mens_fashion', "Men's Fashion"), ('womens_fashion', "Women's Fashion"),
                    ('kids_fashion', "Kids' Fashion"), ('shoes', 'Shoes'),
                    ('bags_accessories', 'Bags & Accessories'),
                    ('furniture', 'Furniture'), ('home_appliances', 'Home Appliances'),
                    ('kitchen', 'Kitchen & Dining'), ('decor', 'Décor & Accessories'),
                    ('health', 'Health & Medical'), ('beauty_skincare', 'Beauty & Skincare'),
                    ('fitness', 'Fitness Equipment'),
                    ('sports', 'Sports Equipment'), ('hobbies_art', 'Hobbies & Art'),
                    ('musical_instruments', 'Musical Instruments'),
                    ('tools', 'Tools & DIY'), ('office_equipment', 'Office Equipment'),
                    ('industrial', 'Industrial & Commercial'),
                    ('other_items', 'Other Items'),
                ],
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='listing',
            name='market_price',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='listings',
                to='core.marketprice',
            ),
        ),
        migrations.AlterField(
            model_name='listing',
            name='category',
            field=models.CharField(
                choices=[
                    ('phones_tablets', 'Phones & Tablets'),
                    ('computers', 'Computers & Laptops'),
                    ('electronics', 'Electronics'),
                    ('gaming', 'Gaming'),
                    ('vehicles', 'Vehicles'),
                    ('fashion', 'Fashion'),
                    ('home_furniture', 'Home & Furniture'),
                    ('health_beauty', 'Health & Beauty'),
                    ('sports_hobbies', 'Sports & Hobbies'),
                    ('tools_equipment', 'Tools & Equipment'),
                    ('other', 'Other'),
                ],
                max_length=50,
            ),
        ),
    ]
