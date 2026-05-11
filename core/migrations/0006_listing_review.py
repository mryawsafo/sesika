from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_seed_categorybaselines'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='rejection_reason',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='listing',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending_review', 'Pending Review'),
                    ('active', 'Active'),
                    ('closed', 'Closed'),
                    ('traded', 'Traded'),
                    ('rejected', 'Rejected'),
                ],
                default='pending_review',
                max_length=20,
            ),
        ),
    ]
