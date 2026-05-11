import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_pricesample'),
    ]

    operations = [
        migrations.CreateModel(
            name='WishlistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('category', models.CharField(blank=True, max_length=50)),
                ('max_budget', models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wishlist_items', to='core.barteruser')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='SavedListing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('saved_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_listings', to='core.barteruser')),
                ('listing', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saves', to='core.listing')),
            ],
            options={'ordering': ['-saved_at']},
        ),
        migrations.AddConstraint(
            model_name='savedlisting',
            constraint=models.UniqueConstraint(fields=['user', 'listing'], name='unique_user_saved_listing'),
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('wishlist_match', 'Wishlist Match'), ('offer_accepted', 'Offer Accepted'), ('offer_rejected', 'Offer Rejected')], max_length=20)),
                ('message', models.CharField(max_length=300)),
                ('link', models.CharField(blank=True, max_length=200)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='core.barteruser')),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]
