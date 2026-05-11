"""
Management command: python manage.py seed_data

Seeds CategoryBaseline records and optional sample listings.
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from core.models import BarterUser, CategoryBaseline, Listing


BASELINES = [
    {'category': 'phones',      'min_value': 200,  'max_value': 5000,  'typical_value': 1500},
    {'category': 'electronics', 'min_value': 100,  'max_value': 8000,  'typical_value': 2000},
    {'category': 'clothing',    'min_value': 20,   'max_value': 500,   'typical_value': 100},
    {'category': 'furniture',   'min_value': 50,   'max_value': 5000,  'typical_value': 600},
    {'category': 'vehicles',    'min_value': 2000, 'max_value': 100000,'typical_value': 20000},
    {'category': 'other',       'min_value': 10,   'max_value': 2000,  'typical_value': 200},
]

SAMPLE_LISTINGS = [
    {
        'phone': '+233201110001', 'name': 'Kofi Mensah',
        'title': 'iPhone 12 Pro Max 256GB', 'category': 'phones',
        'condition': 'used', 'user_estimated_value': 2500,
        'location': 'Accra, Osu',
        'description': 'Space Grey. Battery health 87%. Comes with original box and charger.',
        'want_text': 'Looking for a Samsung Galaxy S22 or GHS 2,000 cash.',
    },
    {
        'phone': '+233201110002', 'name': 'Ama Owusu',
        'title': 'Samsung Galaxy S21 128GB', 'category': 'phones',
        'condition': 'used', 'user_estimated_value': 1800,
        'location': 'Kumasi, Adum',
        'description': 'Phantom Grey. Excellent condition, no cracks. All accessories included.',
        'want_text': 'Want an iPhone 11 or higher, or straight cash.',
    },
    {
        'phone': '+233201110003', 'name': 'Kwame Asante',
        'title': 'Dell XPS 15 Laptop (2021)', 'category': 'electronics',
        'condition': 'used', 'user_estimated_value': 4500,
        'location': 'Accra, East Legon',
        'description': 'Core i7, 16GB RAM, 512GB SSD. Minor scratches on lid. Great for work.',
        'want_text': 'Open to a newer MacBook or GHS 4,000 cash.',
    },
    {
        'phone': '+233201110004', 'name': 'Abena Frimpong',
        'title': 'Recliner Sofa Set (3+1+1)', 'category': 'furniture',
        'condition': 'used', 'user_estimated_value': 1200,
        'location': 'Accra, Tema',
        'description': 'Brown leather recliner. 5 years old but in good shape. No major tears.',
        'want_text': 'Would love a dining table set or GHS 800 cash.',
    },
    {
        'phone': '+233201110005', 'name': 'Nana Boateng',
        'title': 'iPhone SE (2020) – Brand New', 'category': 'phones',
        'condition': 'new', 'user_estimated_value': 1400,
        'location': 'Accra, Airport Residential',
        'description': 'Sealed box. Bought abroad. Comes with Apple warranty receipt.',
        'want_text': 'Looking for a smartwatch (Apple Watch or Samsung Galaxy Watch).',
    },
]


class Command(BaseCommand):
    help = 'Seeds the database with category baselines and sample listings.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--listings', action='store_true',
            help='Also seed sample listings (creates demo users).',
        )

    def handle(self, *args, **options):
        # -- Baselines --
        for data in BASELINES:
            obj, created = CategoryBaseline.objects.update_or_create(
                category=data['category'],
                defaults={
                    'min_value': Decimal(str(data['min_value'])),
                    'max_value': Decimal(str(data['max_value'])),
                    'typical_value': Decimal(str(data['typical_value'])),
                },
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status} baseline: {obj.category}')

        self.stdout.write(self.style.SUCCESS('✅ Category baselines seeded.\n'))

        if not options['listings']:
            self.stdout.write('Tip: run with --listings to also seed sample listings.')
            return

        # -- Sample listings --
        for data in SAMPLE_LISTINGS:
            user, _ = BarterUser.objects.get_or_create(
                phone=data['phone'],
                defaults={'name': data['name'], 'is_verified': True},
            )
            listing, created = Listing.objects.get_or_create(
                user=user, title=data['title'],
                defaults={
                    'category': data['category'],
                    'condition': data['condition'],
                    'user_estimated_value': Decimal(str(data['user_estimated_value'])),
                    'location': data['location'],
                    'description': data['description'],
                    'want_text': data['want_text'],
                },
            )
            if created:
                listing.compute_and_save_value()
                self.stdout.write(f'  Created listing: {listing.title}')
            else:
                self.stdout.write(f'  Already exists:  {listing.title}')

        self.stdout.write(self.style.SUCCESS('✅ Sample listings seeded.'))
