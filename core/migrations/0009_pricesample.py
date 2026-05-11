from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_migrate_categories'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceSample',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('price_ghs', models.DecimalField(decimal_places=2, max_digits=10)),
                ('category', models.CharField(max_length=50)),
                ('scraped_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-scraped_at'],
            },
        ),
        migrations.AddIndex(
            model_name='pricesample',
            index=models.Index(fields=['category', 'scraped_at'], name='core_pricesampl_cat_scraped_idx'),
        ),
    ]
