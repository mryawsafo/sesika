import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_wishlist_notifications'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('budget_tolerance_pct', models.PositiveIntegerField(
                    default=30,
                    help_text='Notify wishlist users even when a listing exceeds their stated budget by up to this percentage. E.g. 30 means notify up to 130% of their budget.',
                )),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
        migrations.AddField(
            model_name='notification',
            name='clicked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='source_listing',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='triggered_notifications',
                to='core.listing',
            ),
        ),
        migrations.AddField(
            model_name='notification',
            name='source_wishlist_item',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='triggered_notifications',
                to='core.wishlistitem',
            ),
        ),
    ]
