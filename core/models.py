import json as _json
import re as _re
import statistics as _statistics
import urllib.parse
import uuid
from datetime import timedelta
from decimal import Decimal

import requests as http_client
from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Category / Subcategory definitions
# ---------------------------------------------------------------------------

CATEGORY_CHOICES = [
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
    ('handmade_crafts', 'Handmade & Crafts'),
    ('art_creative', 'Art & Creative'),
    ('food_plants', 'Food, Plants & Nature'),
    ('services', 'Services & Commissions'),
    ('other', 'Other'),
]

SUBCATEGORY_CHOICES = {
    'phones_tablets': [
        ('iphones', 'iPhones'),
        ('samsung', 'Samsung'),
        ('tecno_itel', 'Tecno / Itel'),
        ('other_android', 'Other Android'),
        ('tablets', 'Tablets'),
        ('phone_accessories', 'Accessories'),
    ],
    'computers': [
        ('laptops', 'Laptops'),
        ('desktops', 'Desktops'),
        ('computer_accessories', 'Accessories'),
    ],
    'electronics': [
        ('tvs', 'TVs & Displays'),
        ('audio', 'Audio & Speakers'),
        ('cameras', 'Cameras & Photography'),
        ('smart_watches', 'Smart Watches'),
        ('other_electronics', 'Other Electronics'),
    ],
    'gaming': [
        ('consoles', 'Consoles'),
        ('games', 'Games'),
        ('gaming_accessories', 'Accessories'),
        ('pc_parts', 'PC Parts & GPUs'),
    ],
    'vehicles': [
        ('cars', 'Cars'),
        ('motorcycles', 'Motorcycles & Scooters'),
        ('trucks', 'Trucks & Commercial'),
    ],
    'fashion': [
        ('mens_fashion', "Men's Fashion"),
        ('womens_fashion', "Women's Fashion"),
        ('kids_fashion', "Kids' Fashion"),
        ('shoes', 'Shoes'),
        ('bags_accessories', 'Bags & Accessories'),
        ('sneakers', 'Sneakers'),
        ('thrift', 'Thrift & Secondhand'),
    ],
    'home_furniture': [
        ('furniture', 'Furniture'),
        ('home_appliances', 'Home Appliances'),
        ('kitchen', 'Kitchen & Dining'),
        ('decor', 'Décor & Accessories'),
    ],
    'health_beauty': [
        ('health', 'Health & Medical'),
        ('beauty_skincare', 'Beauty & Skincare'),
        ('fitness', 'Fitness Equipment'),
    ],
    'sports_hobbies': [
        ('sports', 'Sports Equipment'),
        ('hobbies_art', 'Hobbies & Art'),
        ('musical_instruments', 'Musical Instruments'),
    ],
    'tools_equipment': [
        ('tools', 'Tools & DIY'),
        ('office_equipment', 'Office Equipment'),
        ('industrial', 'Industrial & Commercial'),
    ],
    'handmade_crafts': [
        ('crochet_knitting', 'Crochet & Knitting'),
        ('woodwork', 'Woodwork'),
        ('resin_art', 'Resin Art'),
        ('candles_soaps', 'Candles & Soaps'),
        ('jewellery', 'Jewellery'),
        ('other_handmade', 'Other Handmade'),
    ],
    'art_creative': [
        ('paintings', 'Paintings & Drawings'),
        ('sculptures', 'Sculptures'),
        ('photography', 'Photography'),
        ('digital_art', 'Digital Art'),
        ('music', 'Music & Recordings'),
        ('other_art', 'Other Art'),
    ],
    'food_plants': [
        ('potted_plants', 'Potted Plants'),
        ('dwarf_trees', 'Dwarf Trees & Bonsai'),
        ('flowers', 'Flowers'),
        ('food_produce', 'Food & Produce'),
        ('seeds_seedlings', 'Seeds & Seedlings'),
    ],
    'services': [
        ('graphic_design', 'Graphic Design'),
        ('photography_service', 'Photography Service'),
        ('tailoring', 'Tailoring & Sewing'),
        ('repairs', 'Repairs & Maintenance'),
        ('tutoring', 'Tutoring & Training'),
        ('creative_commission', 'Creative Commission'),
        ('other_service', 'Other Service'),
    ],
    'other': [
        ('other_items', 'Other Items'),
    ],
}

SUBCATEGORY_FLAT_CHOICES = [
    (slug, label)
    for subs in SUBCATEGORY_CHOICES.values()
    for slug, label in subs
]

CONDITION_CHOICES = [
    ('excellent', 'Excellent — like new'),
    ('good', 'Good — fully functional, minor wear'),
    ('fair', 'Fair — fully functional, visible wear'),
    ('for_parts', 'For Parts / Damaged — not fully functional'),
]

CONDITION_MULTIPLIERS = {
    'excellent': Decimal('1.0'),
    'good': Decimal('0.75'),
    'fair': Decimal('0.5'),
    'for_parts': Decimal('0.25'),
}

CONDITION_ORDER = {
    'excellent': 0,
    'good': 1,
    'fair': 2,
    'for_parts': 3,
}

STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('pending_review', 'Pending Review'),
    ('active', 'Active'),
    ('paused', 'Paused'),
    ('traded', 'Traded'),
    ('expired', 'Expired'),
    ('rejected', 'Rejected'),
    ('closed', 'Closed'),
]

GHANA_REGION_CHOICES = [
    ('greater_accra', 'Greater Accra'),
    ('ashanti', 'Ashanti'),
    ('western', 'Western'),
    ('eastern', 'Eastern'),
    ('central', 'Central'),
    ('northern', 'Northern'),
    ('upper_east', 'Upper East'),
    ('upper_west', 'Upper West'),
    ('volta', 'Volta'),
    ('oti', 'Oti'),
    ('bono', 'Bono'),
    ('bono_east', 'Bono East'),
    ('ahafo', 'Ahafo'),
    ('western_north', 'Western North'),
    ('north_east', 'North East'),
    ('savannah', 'Savannah'),
]

GHANA_TOWNS = {
    'greater_accra': [
        'Accra', 'Tema', 'Kasoa', 'Madina', 'Adenta', 'Ashaiman', 'Dome',
        'Achimota', 'Osu', 'Labadi', 'Teshie', 'Nungua', 'Spintex',
        'East Legon', 'Airport Residential', 'Cantonments', 'Labone',
        'Roman Ridge', 'Darkuman', 'Dansoman', 'Weija', 'Ablekuma',
        'Ofankor', 'Pokuase', 'Amasaman', 'Dodowa', 'Prampram', 'Ada', 'Sege',
        'Lashibi', 'Community 25', 'Ashiaman',
    ],
    'ashanti': [
        'Kumasi', 'Obuasi', 'Mampong', 'Ejisu', 'Konongo', 'Agona',
        'Bekwai', 'Juaben', 'Asokwa', 'Nhyiaeso', 'Suame',
        'Asokore Mampong', 'Bantama', 'Adum', 'Kejetia', 'Abuakwa',
        'Tafo', 'Kwadaso', 'Dichemso', 'Manhyia',
    ],
    'western': [
        'Sekondi', 'Takoradi', 'Tarkwa', 'Prestea', 'Axim', 'Shama',
        'Agona Nkwanta', 'Bogoso', 'Halfassini', 'Ankobra', 'Nzema',
    ],
    'eastern': [
        'Koforidua', 'Nkawkaw', 'Asamankese', 'Aburi', 'Akosombo',
        'Oda', 'Akim Oda', 'Nsawam', 'Suhum', 'Donkorkrom', 'Kibi',
        'Mpraeso', 'Kwahu', 'Begoro',
    ],
    'central': [
        'Cape Coast', 'Winneba', 'Mankessim', 'Swedru', 'Assin Fosu',
        'Saltpond', 'Anomabo', 'Dunkwa', 'Twifo Praso', 'Agona Swedru',
        'Elmina', 'Jukwa',
    ],
    'northern': [
        'Tamale', 'Yendi', 'Savelugu', 'Tolon', 'Karaga', 'Gushegu',
        'Kpandai', 'Zabzugu', 'Tatale', 'Demon',
    ],
    'upper_east': [
        'Bolgatanga', 'Bawku', 'Navrongo', 'Zebilla', 'Sandema',
        'Bongo', 'Zuarungu', 'Paga', 'Garu', 'Tempane',
    ],
    'upper_west': [
        'Wa', 'Tumu', 'Lawra', 'Nandom', 'Jirapa', 'Gwolu', 'Funsi',
        'Kaleo', 'Nadowli', 'Hamile',
    ],
    'volta': [
        'Ho', 'Hohoe', 'Keta', 'Sogakope', 'Denu', 'Kpando', 'Aflao',
        'Akatsi', 'Anloga', 'Adidome', 'Dzodze', 'Peki',
    ],
    'oti': [
        'Dambai', 'Nkwanta', 'Jasikan', 'Kadjebi', 'Kete Krachi',
        'Buem', 'Likpe', 'Oti Damanko',
    ],
    'bono': [
        'Sunyani', 'Berekum', 'Dormaa Ahenkro', 'Jinijini', 'Wamfie',
        'Nsoatre', 'Sampa', 'Wenchi',
    ],
    'bono_east': [
        'Techiman', 'Atebubu', 'Kintampo', 'Nkoranza', 'Yeji',
        'Prang', 'Busunya', 'Nsawkaw',
    ],
    'ahafo': [
        'Goaso', 'Kukuom', 'Bechem', 'Acherensua', 'Duayaw Nkwanta',
        'Kenyasi', 'Hwidiem',
    ],
    'western_north': [
        'Sefwi Wiawso', 'Bibiani', 'Enchi', 'Juaboso', 'Aowin',
        'Bia', 'Sefwi Akontombra', 'Bodi',
    ],
    'north_east': [
        'Nalerigu', 'Gambaga', 'Walewale', 'Chereponi', 'Bunkpurugu',
        'Yunyoo', 'Nakpayili',
    ],
    'savannah': [
        'Damongo', 'Bole', 'Salaga', 'Sawla', 'Tuna', 'Daboya',
        'Buipe', 'Yapei',
    ],
}

TRANSACTION_TYPE_CHOICES = [
    ('trade', 'Trade'),
    ('rental', 'Rental'),
]

LISTING_TYPE_CHOICES = [
    ('physical', 'Physical Item'),
    ('handmade', 'Handmade Item'),
    ('service', 'Service / Commission'),
]

LISTING_BEHAVIOUR_CHOICES = [
    ('permanent', 'Permanent'),
    ('temporary', 'Temporary'),
]

DURATION_CHOICES = [
    (7, '7 days'),
    (14, '14 days'),
    (30, '30 days'),
    (60, '60 days'),
]

COLLECTION_METHOD_CHOICES = [
    ('pickup_only', 'Pickup Only'),
    ('delivery_available', 'Delivery Available'),
    ('can_ship', 'Can Ship'),
]

CASH_TOPUP_DIRECTION_CHOICES = [
    ('willing_to_pay', 'Willing to pay a top-up'),
    ('willing_to_receive', 'Willing to receive a top-up'),
    ('neither', 'No cash top-up'),
]

RENTAL_PERIOD_CHOICES = [
    ('hourly', 'Per Hour'),
    ('daily', 'Per Day'),
    ('weekly', 'Per Week'),
    ('per_event', 'Per Event'),
]

CONTACT_REVEAL_CHOICES = [
    ('on_any_offer', 'Reveal to anyone who sends an offer'),
    ('on_accepted_offer', 'Reveal only after I accept an offer'),
]

WANT_TYPE_CHOICES = [
    ('acquire', 'Looking to acquire permanently'),
    ('rent', 'Looking to rent temporarily'),
    ('either', 'Open to either'),
]

TERM_TYPE_CHOICES = [
    ('short_term', 'Short-term (urgent or time-limited)'),
    ('long_term', 'Long-term (ongoing want)'),
]

CONDITION_ACCEPTABLE_CHOICES = [
    ('excellent', 'Excellent or better'),
    ('good', 'Good or better'),
    ('fair', 'Fair or better'),
    ('any', 'Any condition'),
]

NOTIFICATION_FREQUENCY_CHOICES = [
    ('instant', 'Instant'),
    ('daily', 'Daily digest'),
    ('weekly', 'Weekly digest'),
]

MATCH_TIER_CHOICES = [
    ('exact', 'Exact'),
    ('strong', 'Strong'),
    ('potential', 'Potential'),
]

NOTIFICATION_TYPE_CHOICES = [
    ('wishlist_match', 'Wishlist Match'),
    ('offer_received', 'Offer Received'),
    ('offer_accepted', 'Offer Accepted'),
    ('offer_rejected', 'Offer Rejected'),
    ('offer_countered', 'Offer Countered'),
    ('offer_timeout', 'Offer Timeout — Admin Alert'),
    ('seller_demand', 'Seller Demand'),
    ('trade_opportunity', 'Trade Opportunity'),
    ('wishlist_expiring', 'Wishlist Item Expiring'),
    ('listing_expiring', 'Listing Expiring'),
    ('listing_stale', 'Listing Stale — No Matches'),
    ('ai_section_updated', 'AI Section Updated by Admin'),
    ('student_verified', 'Student Email Verified'),
    ('trade_completed', 'Trade Completed'),
    ('rating_received', 'Rating Received'),
]

OFFER_TYPE_CHOICES = [
    ('trade', 'Trade Offer'),
    ('rental', 'Rental Offer'),
]


# ---------------------------------------------------------------------------
# Site-wide settings (singleton — edit via /admin/core/sitesettings/)
# ---------------------------------------------------------------------------

class SiteSettings(models.Model):
    budget_tolerance_pct = models.PositiveIntegerField(
        default=30,
        help_text=(
            'Notify wishlist users even when a listing exceeds their stated budget '
            'by up to this percentage. E.g. 30 means notify up to 130% of their budget.'
        ),
    )
    wishlist_default_expiry_days = models.PositiveIntegerField(
        default=90,
        help_text='Default number of days before a wishlist item expires. Users set short/long term per item.',
    )
    offer_timeout_days = models.PositiveIntegerField(
        default=3,
        help_text='Days before a pending offer is flagged to admin for manual follow-up.',
    )
    listing_stale_days = models.PositiveIntegerField(
        default=60,
        help_text='Days before an active permanent listing with no matches is prompted for review.',
    )

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return 'Site Settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ---------------------------------------------------------------------------
# University domains (admin-configurable for student verification)
# ---------------------------------------------------------------------------

class UniversityDomain(models.Model):
    domain = models.CharField(max_length=100, unique=True, help_text='e.g. ug.edu.gh')
    university_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['university_name']
        verbose_name = 'University Email Domain'
        verbose_name_plural = 'University Email Domains'

    def __str__(self):
        return f"{self.university_name} ({self.domain})"


# ---------------------------------------------------------------------------
# Category baselines (fallback when no market price is cached)
# ---------------------------------------------------------------------------

class CategoryBaseline(models.Model):
    category = models.CharField(max_length=50, unique=True)
    min_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_value = models.DecimalField(max_digits=10, decimal_places=2)
    typical_value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category} (typical: {self.typical_value})"


class Category(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, blank=True, help_text='Emoji icon, e.g. 📱')
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'label']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.label


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    slug = models.SlugField(max_length=50)
    label = models.CharField(max_length=100)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [['category', 'slug']]
        ordering = ['category__display_order', 'display_order', 'label']
        verbose_name = 'Subcategory'
        verbose_name_plural = 'Subcategories'

    def __str__(self):
        return f"{self.category.label} › {self.label}"


# ---------------------------------------------------------------------------
# DB-driven category cache helpers
# ---------------------------------------------------------------------------

def get_active_categories():
    try:
        return list(
            Category.objects.filter(is_active=True)
            .values_list('slug', 'label')
            .order_by('display_order', 'label')
        )
    except Exception:
        return list(CATEGORY_CHOICES)


def get_subcategory_map():
    try:
        from collections import defaultdict
        result = defaultdict(list)
        for sub in (
            Subcategory.objects.filter(is_active=True)
            .select_related('category')
            .order_by('category__display_order', 'display_order', 'label')
        ):
            result[sub.category.slug].append((sub.slug, sub.label))
        return dict(result)
    except Exception:
        return dict(SUBCATEGORY_CHOICES)


def invalidate_category_cache():
    pass


# ---------------------------------------------------------------------------
# Category-specific attribute schemas
# ---------------------------------------------------------------------------

CATEGORY_ATTRIBUTE_SCHEMAS = {

    # ── Phones & Tablets ────────────────────────────────────────────────────
    'phones_tablets': {
        'trade': [
            {'name': 'storage_gb',          'label': 'Storage',                   'type': 'select',   'required': True,
             'options': [['16','16 GB'],['32','32 GB'],['64','64 GB'],['128','128 GB'],['256','256 GB'],['512','512 GB'],['1024','1 TB']]},
            {'name': 'ram_gb',              'label': 'RAM',                        'type': 'select',   'required': False,
             'options': [['2','2 GB'],['3','3 GB'],['4','4 GB'],['6','6 GB'],['8','8 GB'],['12','12 GB'],['16','16 GB']]},
            {'name': 'network',             'label': 'Network',                    'type': 'select',   'required': False,
             'options': [['5g','5G'],['4g','4G LTE'],['3g','3G']]},
            {'name': 'sim_slots',           'label': 'SIM Slots',                  'type': 'select',   'required': False,
             'options': [['single','Single SIM'],['dual','Dual SIM']]},
            {'name': 'battery_health',      'label': 'Battery Health (%)',         'type': 'number',   'required': False, 'min': 1, 'max': 100,
             'placeholder': 'e.g. 87 — iPhones only'},
            {'name': 'original_box',        'label': 'Original box & accessories', 'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'storage_gb',          'label': 'Storage',                   'type': 'select',   'required': False,
             'options': [['32','32 GB'],['64','64 GB'],['128','128 GB'],['256','256 GB']]},
            {'name': 'network',             'label': 'Network',                    'type': 'select',   'required': False,
             'options': [['5g','5G'],['4g','4G LTE'],['3g','3G']]},
            {'name': 'sim_included',        'label': 'Local SIM card included',    'type': 'checkbox', 'required': False},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
        ],
    },

    # ── Computers & Laptops ─────────────────────────────────────────────────
    'computers': {
        'trade': [
            {'name': 'ram_gb',              'label': 'RAM',                        'type': 'select',   'required': True,
             'options': [['4','4 GB'],['8','8 GB'],['12','12 GB'],['16','16 GB'],['32','32 GB'],['64','64 GB']]},
            {'name': 'storage_gb',          'label': 'Storage Size',               'type': 'select',   'required': True,
             'options': [['128','128 GB'],['256','256 GB'],['512','512 GB'],['1000','1 TB'],['2000','2 TB']]},
            {'name': 'storage_type',        'label': 'Storage Type',               'type': 'select',   'required': False,
             'options': [['ssd','SSD'],['hdd','HDD'],['ssd_hdd','SSD + HDD']]},
            {'name': 'processor',           'label': 'Processor',                  'type': 'select',   'required': False,
             'options': [['intel_i3','Intel Core i3'],['intel_i5','Intel Core i5'],['intel_i7','Intel Core i7'],
                         ['intel_i9','Intel Core i9'],['amd_ryzen5','AMD Ryzen 5'],['amd_ryzen7','AMD Ryzen 7'],
                         ['apple_m1','Apple M1'],['apple_m2','Apple M2'],['apple_m3','Apple M3'],['other','Other']]},
            {'name': 'screen_size',         'label': 'Screen Size (inches)',        'type': 'select',   'required': False,
             'options': [['11','11"'],['13','13"'],['14','14"'],['15','15.6"'],['16','16"'],['17','17"']]},
            {'name': 'charger_included',    'label': 'Charger included',           'type': 'checkbox', 'required': False},
            {'name': 'touch_screen',        'label': 'Touchscreen',                'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'ram_gb',              'label': 'RAM',                        'type': 'select',   'required': False,
             'options': [['4','4 GB'],['8','8 GB'],['16','16 GB'],['32','32 GB']]},
            {'name': 'processor',           'label': 'Processor',                  'type': 'select',   'required': False,
             'options': [['intel_i5','Intel i5'],['intel_i7','Intel i7'],['amd_ryzen5','AMD Ryzen 5'],
                         ['apple_m1','Apple M1'],['apple_m2','Apple M2'],['apple_m3','Apple M3']]},
            {'name': 'preloaded_software',  'label': 'Preloaded software',         'type': 'text',     'required': False,
             'placeholder': 'e.g. MS Office, Adobe CC, AutoCAD'},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
        ],
    },

    # ── Electronics ─────────────────────────────────────────────────────────
    'electronics': {
        'trade': [
            {'name': 'screen_size',         'label': 'Screen Size (inches)',        'type': 'number',   'required': False,
             'placeholder': 'e.g. 55 — TVs & monitors only', 'min': 5, 'max': 120},
            {'name': 'resolution',          'label': 'Resolution',                 'type': 'select',   'required': False,
             'options': [['hd','HD 720p'],['fhd','Full HD 1080p'],['4k','4K UHD'],['8k','8K']]},
            {'name': 'smart',               'label': 'Smart / WiFi enabled',       'type': 'checkbox', 'required': False},
            {'name': 'wireless',            'label': 'Wireless / Bluetooth',       'type': 'checkbox', 'required': False},
            {'name': 'remote_included',     'label': 'Remote / accessories included','type': 'checkbox','required': False},
        ],
        'rental': [
            {'name': 'screen_size',         'label': 'Screen Size (inches)',        'type': 'number',   'required': False,
             'placeholder': 'e.g. 55 — TVs only', 'min': 5, 'max': 120},
            {'name': 'smart',               'label': 'Smart / WiFi enabled',       'type': 'checkbox', 'required': False},
            {'name': 'quantity_available',  'label': 'Units available',            'type': 'number',   'required': False,
             'placeholder': 'e.g. 2 speakers, 1 projector'},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
        ],
    },

    # ── Gaming ──────────────────────────────────────────────────────────────
    'gaming': {
        'trade': [
            {'name': 'platform',            'label': 'Platform',                   'type': 'select',   'required': True,
             'options': [['ps5','PlayStation 5'],['ps4','PlayStation 4'],['ps3','PlayStation 3'],
                         ['xbox_series','Xbox Series X/S'],['xbox_one','Xbox One'],
                         ['nintendo_switch','Nintendo Switch'],['pc','PC / Steam Deck'],['other','Other']]},
            {'name': 'storage_gb',          'label': 'Console Storage',            'type': 'select',   'required': False,
             'options': [['500','500 GB'],['825','825 GB'],['1000','1 TB'],['2000','2 TB']]},
            {'name': 'controllers',         'label': 'Controllers included',       'type': 'number',   'required': False, 'min': 0, 'max': 8},
            {'name': 'games_count',         'label': 'Games included',             'type': 'number',   'required': False, 'min': 0},
            {'name': 'game_titles',         'label': 'Game titles (if any)',       'type': 'text',     'required': False,
             'placeholder': 'e.g. FIFA 25, GTA V, God of War'},
        ],
        'rental': [
            {'name': 'platform',            'label': 'Platform',                   'type': 'select',   'required': True,
             'options': [['ps5','PlayStation 5'],['ps4','PlayStation 4'],['xbox_series','Xbox Series X/S'],
                         ['nintendo_switch','Nintendo Switch'],['other','Other']]},
            {'name': 'controllers',         'label': 'Controllers included',       'type': 'number',   'required': False, 'min': 1, 'max': 8},
            {'name': 'games_count',         'label': 'Games / titles available',   'type': 'number',   'required': False},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'per_event_price',     'label': 'Party / event Rate (GHS)',   'type': 'number',   'required': False},
            {'name': 'setup_included',      'label': 'Setup & teardown included',  'type': 'checkbox', 'required': False},
        ],
    },

    # ── Vehicles ────────────────────────────────────────────────────────────
    'vehicles': {
        'trade': [
            {'name': 'year',                'label': 'Year',                       'type': 'number',   'required': True,  'min': 1960, 'max': 2030},
            {'name': 'transmission',        'label': 'Transmission',               'type': 'select',   'required': True,
             'options': [['manual','Manual'],['automatic','Automatic'],['semi_auto','Semi-Automatic']]},
            {'name': 'fuel_type',           'label': 'Fuel Type',                  'type': 'select',   'required': True,
             'options': [['petrol','Petrol'],['diesel','Diesel'],['electric','Electric'],['hybrid','Hybrid'],['lpg','LPG']]},
            {'name': 'mileage_km',          'label': 'Mileage (km)',               'type': 'number',   'required': False},
            {'name': 'seating_capacity',    'label': 'Seating Capacity',           'type': 'number',   'required': False},
            {'name': 'cargo_capacity',      'label': 'Cargo Capacity',             'type': 'text',     'required': False,
             'placeholder': 'e.g. 1.5 tonnes'},
            {'name': 'drivetrain',          'label': 'Drivetrain',                 'type': 'select',   'required': False,
             'options': [['2wd','2WD'],['4wd','4WD'],['awd','AWD']]},
            {'name': 'ac',                  'label': 'Air Conditioning',           'type': 'checkbox', 'required': False},
            {'name': 'power_steering',      'label': 'Power Steering',             'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'year',                'label': 'Year',                       'type': 'number',   'required': True,  'min': 1960, 'max': 2030},
            {'name': 'transmission',        'label': 'Transmission',               'type': 'select',   'required': True,
             'options': [['manual','Manual'],['automatic','Automatic'],['semi_auto','Semi-Automatic']]},
            {'name': 'fuel_type',           'label': 'Fuel Type',                  'type': 'select',   'required': True,
             'options': [['petrol','Petrol'],['diesel','Diesel'],['electric','Electric'],['hybrid','Hybrid'],['lpg','LPG']]},
            {'name': 'mileage_km',          'label': 'Current Mileage (km)',       'type': 'number',   'required': False},
            {'name': 'seating_capacity',    'label': 'Seating Capacity',           'type': 'number',   'required': False},
            {'name': 'ac',                  'label': 'Air Conditioning',           'type': 'checkbox', 'required': False},
            {'name': 'power_steering',      'label': 'Power Steering',             'type': 'checkbox', 'required': False},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
            {'name': 'monthly_price',       'label': 'Monthly Rate (GHS)',         'type': 'number',   'required': False},
            {'name': 'driver_included',     'label': 'Driver Included',            'type': 'checkbox', 'required': False},
            {'name': 'self_drive',          'label': 'Self-Drive Option',          'type': 'checkbox', 'required': False},
            {'name': 'fuel_policy',         'label': 'Fuel Policy',                'type': 'select',   'required': False,
             'options': [['full_to_full','Full to Full'],['same_level','Same Level'],['included','Fuel Included']]},
            {'name': 'mileage_limit',       'label': 'Mileage Limit',             'type': 'text',     'required': False,
             'placeholder': 'e.g. 200 km/day or Unlimited'},
        ],
    },

    # ── Fashion ─────────────────────────────────────────────────────────────
    'fashion': {
        'trade': [
            {'name': 'size',                'label': 'Size',                       'type': 'text',     'required': True,
             'placeholder': 'e.g. M, L, UK 10, EU 42, 32W/30L'},
            {'name': 'gender',              'label': 'For',                        'type': 'select',   'required': True,
             'options': [['women',"Women's"],['men',"Men's"],['unisex','Unisex'],['girls',"Girls'"],['boys',"Boys'"]]},
            {'name': 'color',               'label': 'Colour',                     'type': 'text',     'required': False,
             'placeholder': 'e.g. Black, Navy Blue, Kente print'},
            {'name': 'material',            'label': 'Material / Fabric',          'type': 'text',     'required': False,
             'placeholder': 'e.g. 100% Cotton, Polyester blend, Kente'},
            {'name': 'new_with_tags',       'label': 'New with tags (unworn)',     'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'size',                'label': 'Size',                       'type': 'text',     'required': True,
             'placeholder': 'e.g. M, UK 10, EU 42'},
            {'name': 'gender',              'label': 'For',                        'type': 'select',   'required': True,
             'options': [['women',"Women's"],['men',"Men's"],['unisex','Unisex']]},
            {'name': 'occasion',            'label': 'Occasion',                   'type': 'select',   'required': False,
             'options': [['formal','Formal / Corporate'],['casual','Casual'],['wedding','Wedding / Engagement'],
                         ['traditional','Traditional / Kente / Kaba'],['party','Party / Night out'],
                         ['costume','Costume / Themed event']]},
            {'name': 'dry_cleaning_fee',    'label': 'Dry cleaning fee (GHS)',     'type': 'number',   'required': False},
            {'name': 'per_day_price',       'label': 'Per-day Rate (GHS)',         'type': 'number',   'required': False},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
        ],
    },

    # ── Home & Furniture ────────────────────────────────────────────────────
    'home_furniture': {
        'trade': [
            {'name': 'material',            'label': 'Material',                   'type': 'select',   'required': False,
             'options': [['wood','Wood'],['metal','Metal'],['glass','Glass'],['plastic','Plastic'],
                         ['fabric','Fabric / Upholstered'],['rattan','Rattan / Wicker'],['mixed','Mixed materials']]},
            {'name': 'color',               'label': 'Colour / Finish',            'type': 'text',     'required': False,
             'placeholder': 'e.g. Brown, White, Oak'},
            {'name': 'dimensions',          'label': 'Dimensions (L × W × H cm)', 'type': 'text',     'required': False,
             'placeholder': 'e.g. 180 × 90 × 75'},
            {'name': 'seating_capacity',    'label': 'Seating capacity',           'type': 'number',   'required': False,
             'placeholder': 'e.g. 3 (sofas / chairs)'},
            {'name': 'delivery_possible',   'label': 'Can arrange delivery',       'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'material',            'label': 'Material',                   'type': 'select',   'required': False,
             'options': [['wood','Wood'],['metal','Metal'],['plastic','Plastic'],['fabric','Fabric'],['mixed','Mixed']]},
            {'name': 'color',               'label': 'Colour',                     'type': 'text',     'required': False,
             'placeholder': 'e.g. White, Brown, Black'},
            {'name': 'quantity_available',  'label': 'Units available',            'type': 'number',   'required': False,
             'placeholder': 'e.g. 20 chairs, 5 tables'},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'delivery_setup',      'label': 'Delivery & setup included',  'type': 'checkbox', 'required': False},
        ],
    },

    # ── Health & Beauty ─────────────────────────────────────────────────────
    'health_beauty': {
        'trade': [
            {'name': 'item_type',           'label': 'Item type',                  'type': 'select',   'required': False,
             'options': [['skincare','Skincare / Moisturiser'],['haircare','Haircare'],['makeup','Makeup / Cosmetics'],
                         ['fragrance','Fragrance / Perfume'],['supplements','Supplements / Vitamins'],
                         ['device','Health / Beauty device'],['medical','Medical equipment']]},
            {'name': 'skin_type',           'label': 'Suitable skin type',         'type': 'select',   'required': False,
             'options': [['all','All skin types'],['oily','Oily'],['dry','Dry'],
                         ['combination','Combination'],['sensitive','Sensitive']]},
            {'name': 'quantity_remaining',  'label': 'Amount remaining',           'type': 'text',     'required': False,
             'placeholder': 'e.g. Unopened, ~80% full, 30 tablets left'},
            {'name': 'expiry_date',         'label': 'Expiry / best before',       'type': 'text',     'required': False,
             'placeholder': 'e.g. 06/2026'},
        ],
        'rental': [
            {'name': 'item_type',           'label': 'Equipment type',             'type': 'select',   'required': False,
             'options': [['massage','Massage / spa equipment'],['physio','Physiotherapy equipment'],
                         ['monitor','Health monitor / device'],['salon','Salon equipment'],['other','Other']]},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
        ],
    },

    # ── Sports & Hobbies ────────────────────────────────────────────────────
    'sports_hobbies': {
        'trade': [
            {'name': 'sport_activity',      'label': 'Sport / Activity',           'type': 'text',     'required': False,
             'placeholder': 'e.g. Football, Swimming, Cycling, Basketball'},
            {'name': 'size',                'label': 'Size / Spec',                'type': 'text',     'required': False,
             'placeholder': 'e.g. Size 5, 26" wheel, UK 10, Medium frame'},
            {'name': 'level',               'label': 'Suitable for',               'type': 'select',   'required': False,
             'options': [['all','All levels'],['beginner','Beginner / Recreational'],
                         ['intermediate','Intermediate'],['professional','Professional / Competitive']]},
        ],
        'rental': [
            {'name': 'sport_activity',      'label': 'Sport / Activity',           'type': 'text',     'required': False,
             'placeholder': 'e.g. Cycling, Camping, Watersports'},
            {'name': 'quantity_available',  'label': 'Units available',            'type': 'number',   'required': False},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
        ],
    },

    # ── Tools & Equipment ───────────────────────────────────────────────────
    'tools_equipment': {
        'trade': [
            {'name': 'power_source',        'label': 'Power source',               'type': 'select',   'required': False,
             'options': [['electric','Electric / Mains'],['battery','Battery / Cordless'],
                         ['manual','Manual / Hand tool'],['petrol','Petrol / Engine'],['solar','Solar']]},
            {'name': 'voltage',             'label': 'Voltage',                    'type': 'select',   'required': False,
             'options': [['220v','220 / 240V'],['110v','110V'],['universal','Universal / Dual voltage']]},
            {'name': 'accessories_included','label': 'Accessories / bits included', 'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'power_source',        'label': 'Power source',               'type': 'select',   'required': False,
             'options': [['electric','Electric / Mains'],['battery','Battery / Cordless'],
                         ['manual','Manual'],['petrol','Petrol / Engine']]},
            {'name': 'quantity_available',  'label': 'Units available',            'type': 'number',   'required': False},
            {'name': 'daily_price',         'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
            {'name': 'security_deposit',    'label': 'Security deposit (GHS)',     'type': 'number',   'required': False},
            {'name': 'training_provided',   'label': 'Usage guidance provided',    'type': 'checkbox', 'required': False},
        ],
    },

    # ── Handmade & Crafts ───────────────────────────────────────────────────
    'handmade_crafts': {
        'trade': [
            {'name': 'materials',           'label': 'Main materials',             'type': 'text',     'required': False,
             'placeholder': 'e.g. Cotton yarn, Mahogany, Beeswax, Resin'},
            {'name': 'dimensions',          'label': 'Size / Dimensions',          'type': 'text',     'required': False,
             'placeholder': 'e.g. 30 × 20 cm, One-size, S/M/L'},
            {'name': 'quantity_available',  'label': 'Units in stock',             'type': 'number',   'required': False, 'min': 1},
            {'name': 'made_to_order',       'label': 'Custom / made-to-order available','type': 'checkbox','required': False},
            {'name': 'production_days',     'label': 'Production time (days)',     'type': 'number',   'required': False,
             'placeholder': 'e.g. 5 (if made to order)'},
        ],
        'rental': [
            {'name': 'item_type',           'label': 'Item type',                  'type': 'text',     'required': False,
             'placeholder': 'e.g. Centrepieces, Backdrops, Decor props'},
            {'name': 'quantity_available',  'label': 'Units available',            'type': 'number',   'required': False},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
            {'name': 'setup_included',      'label': 'Setup / styling included',   'type': 'checkbox', 'required': False},
        ],
    },

    # ── Art & Creative ──────────────────────────────────────────────────────
    'art_creative': {
        'trade': [
            {'name': 'medium',              'label': 'Medium / Type',              'type': 'select',   'required': False,
             'options': [['oil','Oil paint'],['acrylic','Acrylic'],['watercolor','Watercolour'],
                         ['pencil','Pencil / Charcoal'],['mixed_media','Mixed media'],
                         ['photography_print','Photography print'],['digital_print','Digital / Giclee print'],
                         ['sculpture','Sculpture'],['textile','Textile / Fabric art'],['other','Other']]},
            {'name': 'dimensions',          'label': 'Dimensions',                 'type': 'text',     'required': False,
             'placeholder': 'e.g. A3, 60 × 90 cm, 18 × 24 inches'},
            {'name': 'original_or_print',   'label': 'Original or print',          'type': 'select',   'required': True,
             'options': [['original','Original artwork (one-of-a-kind)'],['limited_print','Limited edition print'],
                         ['open_print','Open edition print'],['digital_file','Digital file / licence']]},
            {'name': 'signed',              'label': 'Signed by artist',           'type': 'checkbox', 'required': False},
            {'name': 'framed',              'label': 'Framed / mounted',           'type': 'checkbox', 'required': False},
        ],
        'rental': [
            {'name': 'medium',              'label': 'Type',                       'type': 'select',   'required': False,
             'options': [['painting','Painting'],['photography_print','Photography print'],
                         ['sculpture','Sculpture'],['textile','Textile / Wall hanging'],['other','Other']]},
            {'name': 'dimensions',          'label': 'Dimensions',                 'type': 'text',     'required': False,
             'placeholder': 'e.g. 60 × 90 cm'},
            {'name': 'framed',              'label': 'Framed / ready to hang',     'type': 'checkbox', 'required': False},
            {'name': 'monthly_price',       'label': 'Monthly Rate (GHS)',         'type': 'number',   'required': False},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
        ],
    },

    # ── Food, Plants & Nature ───────────────────────────────────────────────
    'food_plants': {
        'trade': [
            {'name': 'item_type',           'label': 'Type',                       'type': 'select',   'required': False,
             'options': [['indoor_plant','Indoor plant'],['outdoor_plant','Outdoor / Garden plant'],
                         ['succulent','Succulent / Cactus'],['tropical','Tropical plant'],
                         ['fruit_tree','Fruit tree / seedling'],['herbs','Herbs / Medicinal plant'],
                         ['food_produce','Food & Produce'],['seeds','Seeds / Bulbs']]},
            {'name': 'pot_size',            'label': 'Pot size',                   'type': 'select',   'required': False,
             'options': [['small','Small (under 15 cm)'],['medium','Medium (15–30 cm)'],
                         ['large','Large (over 30 cm)'],['unpotted','Unpotted / bare root'],['na','Not applicable']]},
            {'name': 'care_level',          'label': 'Care difficulty',            'type': 'select',   'required': False,
             'options': [['easy','Easy — thrives with minimal attention'],
                         ['moderate','Moderate — weekly watering & light'],
                         ['demanding','Demanding — needs daily attention']]},
            {'name': 'quantity',            'label': 'Quantity / amount',          'type': 'text',     'required': False,
             'placeholder': 'e.g. 1 plant, 500 g, 1 bunch'},
        ],
        'rental': [
            {'name': 'item_type',           'label': 'Type',                       'type': 'select',   'required': False,
             'options': [['indoor_plant','Indoor / potted plant'],['tropical','Tropical / statement plant'],
                         ['floral_arrangement','Floral arrangement'],['artificial','Artificial plant / tree']]},
            {'name': 'quantity_available',  'label': 'Units available',            'type': 'number',   'required': False,
             'placeholder': 'e.g. 10 plants for event staging'},
            {'name': 'per_event_price',     'label': 'Per-event Rate (GHS)',       'type': 'number',   'required': False},
            {'name': 'weekly_price',        'label': 'Weekly Rate (GHS)',          'type': 'number',   'required': False},
            {'name': 'delivery_setup',      'label': 'Delivery & styling included','type': 'checkbox', 'required': False},
        ],
    },

    # ── Services & Commissions ──────────────────────────────────────────────
    'services': {
        'trade': [
            {'name': 'delivery_method',     'label': 'How it is delivered',        'type': 'select',   'required': True,
             'options': [['in_person','In-person (client comes to me / I travel)'],
                         ['remote','Remote / Online'],['both','Both options available']]},
            {'name': 'turnaround_days',     'label': 'Typical turnaround (days)',  'type': 'number',   'required': False,
             'placeholder': 'e.g. 3', 'min': 0},
            {'name': 'revisions',           'label': 'Revision rounds included',   'type': 'number',   'required': False,
             'placeholder': 'e.g. 2', 'min': 0},
            {'name': 'portfolio_link',      'label': 'Portfolio / sample work',    'type': 'text',     'required': False,
             'placeholder': 'e.g. instagram.com/yourpage or behance.net/you'},
        ],
        'rental': [
            {'name': 'delivery_method',     'label': 'Availability',               'type': 'select',   'required': True,
             'options': [['in_person','In-person'],['remote','Remote / Online'],['both','Both']]},
            {'name': 'hourly_rate',         'label': 'Hourly Rate (GHS)',          'type': 'number',   'required': False},
            {'name': 'daily_rate',          'label': 'Daily Rate (GHS)',           'type': 'number',   'required': False},
            {'name': 'min_booking_hours',   'label': 'Minimum booking (hours)',    'type': 'number',   'required': False,
             'placeholder': 'e.g. 2'},
        ],
    },
}


# ---------------------------------------------------------------------------
# Market price cache (keyed by normalised item title, populated from Jiji)
# ---------------------------------------------------------------------------

def normalize_item_key(title: str) -> str:
    key = title.lower().strip()
    key = _re.sub(r'[^a-z0-9\s]', ' ', key)
    key = _re.sub(r'\s+', ' ', key).strip()
    return key[:200]


def fetch_market_price_from_jiji(title: str) -> Decimal | None:
    """Live Jiji search — only used when PriceSample DB has no match."""
    query = urllib.parse.quote_plus(title)
    try:
        resp = http_client.get(
            f"https://jiji.com.gh/search?query={query}",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; Sesika/1.0)'},
        )
        resp.raise_for_status()
        prices_raw = _re.findall(r'qa-advert-price[^>]*>\s*GH[₵C]\s*([\d,]+)', resp.text)
        prices = [int(p.replace(',', '')) for p in prices_raw if p]
        if prices:
            return Decimal(str(int(_statistics.median(prices))))
    except Exception:
        pass
    return None


def _price_from_samples(title: str) -> Decimal | None:
    """Compute median from the PriceSample DB for items matching the title keywords."""
    tokens = [t for t in normalize_item_key(title).split() if len(t) > 2][:4]
    if not tokens:
        return None
    qs = PriceSample.objects.all()
    for token in tokens:
        qs = qs.filter(title__icontains=token)
    prices = list(qs.values_list('price_ghs', flat=True)[:50])
    if len(prices) >= 3:
        return Decimal(str(int(_statistics.median([float(p) for p in prices]))))
    return None


def _resolve_price(title: str) -> tuple[Decimal, str] | tuple[None, None]:
    """PriceSample DB first; live Jiji search only if no match."""
    price = _price_from_samples(title)
    if price:
        return price, 'jiji_db'
    price = fetch_market_price_from_jiji(title)
    if price:
        return price, 'jiji_live'
    return None, None


class MarketPrice(models.Model):
    item_key = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=50)
    subcategory = models.CharField(max_length=50, blank=True)
    price_ghs = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=20, default='jiji')
    sample_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    STALE_DAYS = 30

    class Meta:
        ordering = ['item_key']

    def __str__(self):
        return f"{self.item_key} — GHS {self.price_ghs} ({self.source})"

    @property
    def is_stale(self):
        return (timezone.now() - self.last_updated).days >= self.STALE_DAYS


class PriceSample(models.Model):
    """Individual Jiji listing scraped by scrape_jiji_prices. Auto-purged after 30 days."""
    title = models.CharField(max_length=300)
    price_ghs = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50)
    scraped_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scraped_at']
        indexes = [models.Index(fields=['category', 'scraped_at'])]

    def __str__(self):
        return f"{self.title} — GHS {self.price_ghs}"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class BarterUser(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    whatsapp_number = models.CharField(max_length=20, blank=True)
    location_region = models.CharField(
        max_length=50, choices=GHANA_REGION_CHOICES, blank=True
    )
    location_city = models.CharField(max_length=100, blank=True)
    location_neighbourhood = models.CharField(max_length=100, blank=True)
    contact_reveal_preference = models.CharField(
        max_length=20,
        choices=CONTACT_REVEAL_CHOICES,
        default='on_any_offer',
    )
    portfolio_url = models.URLField(blank=True, help_text='Link to your portfolio, Instagram, or website.')
    website_url = models.URLField(blank=True, help_text='Optional additional URL.')
    student_email = models.EmailField(blank=True)
    is_student_verified = models.BooleanField(default=False)
    student_verified_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or 'User'} ({self.phone})"

    @property
    def display_whatsapp(self):
        return self.whatsapp_number or self.phone

    @property
    def location_display(self):
        parts = [p for p in [self.location_city, self.get_location_region_display()] if p]
        return ', '.join(parts) if parts else ''

    @property
    def completed_trades_count(self):
        from django.db.models import Q
        return Offer.objects.filter(
            Q(from_user=self) | Q(to_user=self),
            status='accepted',
        ).count()


# ---------------------------------------------------------------------------
# Campus Groups
# ---------------------------------------------------------------------------

class CampusGroup(models.Model):
    name = models.CharField(max_length=200)
    university_name = models.CharField(max_length=200)
    domain = models.ForeignKey(
        UniversityDomain, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='campus_groups',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['university_name']

    def __str__(self):
        return self.name


class CampusMembership(models.Model):
    user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='campus_memberships')
    group = models.ForeignKey(CampusGroup, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'group']]

    def __str__(self):
        return f"{self.user} in {self.group}"


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

class Listing(models.Model):
    user = models.ForeignKey(
        BarterUser, on_delete=models.CASCADE, related_name='listings'
    )
    # Core details
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, blank=True)
    subcategory = models.CharField(max_length=50, blank=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, blank=True)
    listing_type = models.CharField(max_length=20, choices=LISTING_TYPE_CHOICES, default='physical')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES, default='trade')

    # Listing duration behaviour
    listing_behaviour = models.CharField(
        max_length=20, choices=LISTING_BEHAVIOUR_CHOICES, default='permanent'
    )
    duration_days = models.PositiveIntegerField(
        null=True, blank=True,
        choices=DURATION_CHOICES,
        help_text='Required for temporary listings.',
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    # Value
    user_estimated_value = models.DecimalField(max_digits=10, decimal_places=2)
    system_estimated_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    final_estimated_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    market_price = models.ForeignKey(
        MarketPrice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='listings',
    )

    # Location
    location_region = models.CharField(max_length=50, choices=GHANA_REGION_CHOICES, blank=True)
    location_city = models.CharField(max_length=100, blank=True)
    location_neighbourhood = models.CharField(max_length=100, blank=True)

    # Trade preferences
    want_text = models.TextField(help_text='What do you want in exchange?')
    collection_method = models.CharField(
        max_length=20, choices=COLLECTION_METHOD_CHOICES, default='pickup_only'
    )
    cash_topup_direction = models.CharField(
        max_length=20, choices=CASH_TOPUP_DIRECTION_CHOICES, default='neither'
    )

    # Category-specific: tech / fashion
    brand = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=50, blank=True)
    colour = models.CharField(max_length=50, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Male'), ('female', 'Female'), ('unisex', 'Unisex'), ('kids', 'Kids')],
        blank=True,
    )

    # Category-specific: handmade
    materials_used = models.TextField(blank=True)

    # Category-specific: service / commission
    service_scope = models.TextField(blank=True)
    service_timeline_days = models.PositiveIntegerField(null=True, blank=True)

    # Category-specific: repair / refurbished
    repair_description = models.TextField(blank=True)
    warranty_offered = models.BooleanField(default=False)
    warranty_duration_days = models.PositiveIntegerField(null=True, blank=True)

    # Rental-specific
    rental_period_unit = models.CharField(max_length=20, choices=RENTAL_PERIOD_CHOICES, blank=True)
    rental_payment_description = models.TextField(blank=True)
    deposit_required = models.BooleanField(default=False)
    deposit_description = models.TextField(blank=True)
    availability_notes = models.TextField(blank=True)
    rental_conditions = models.TextField(blank=True)

    # AI enrichment
    ai_enrichment = models.JSONField(null=True, blank=True)
    ai_enrichment_hidden = models.BooleanField(default=False)
    ai_enrichment_flagged = models.BooleanField(default=False)
    ai_enrichment_admin_edited = models.BooleanField(default=False)

    # Category-specific structured attributes (e.g. vehicle specs)
    attributes = models.JSONField(null=True, blank=True)

    # SEO fields (populated by AI on approval)
    slug = models.SlugField(max_length=230, unique=True, blank=True)
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)

    # User-suggested category (filled when user picks "Other" on the listing form)
    suggested_category = models.CharField(max_length=100, blank=True)
    suggested_subcategory = models.CharField(max_length=100, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_review')
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.listing_behaviour == 'temporary' and self.duration_days and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=self.duration_days)
        super().save(*args, **kwargs)
        if not self.slug and self.pk:
            from django.utils.text import slugify
            self.slug = f"{slugify(self.title)[:200]}-{self.pk}"
            super().save(update_fields=['slug'])

    @property
    def primary_photo(self):
        return self.photos.order_by('order').first()

    @property
    def all_photos(self):
        return self.photos.order_by('order')

    @property
    def location_display(self):
        parts = [p for p in [self.location_city, self.get_location_region_display()] if p]
        return ', '.join(parts) if parts else ''

    @property
    def offer_count(self):
        return self.offers.count()

    def compute_and_save_value(self):
        multiplier = CONDITION_MULTIPLIERS.get(self.condition, Decimal('1.0'))
        item_key = normalize_item_key(self.title)

        mp = None
        try:
            mp = MarketPrice.objects.get(item_key=item_key)
            if mp.is_stale:
                price, source = _resolve_price(self.title)
                if price:
                    mp.price_ghs = price
                    mp.source = source
                    mp.sample_count += 1
                    mp.save(update_fields=['price_ghs', 'source', 'sample_count'])
        except MarketPrice.DoesNotExist:
            price, source = _resolve_price(self.title)
            if price:
                mp = MarketPrice.objects.create(
                    item_key=item_key,
                    category=self.category,
                    subcategory=self.subcategory,
                    price_ghs=price,
                    source=source,
                )

        if mp is not None:
            try:
                baseline = CategoryBaseline.objects.get(category=self.category)
                if mp.price_ghs < baseline.min_value:
                    mp = None
            except CategoryBaseline.DoesNotExist:
                pass

        if mp is not None:
            base_price = mp.price_ghs
        else:
            try:
                baseline = CategoryBaseline.objects.get(category=self.category)
                base_price = baseline.typical_value
            except CategoryBaseline.DoesNotExist:
                base_price = self.user_estimated_value

        self.market_price = mp
        self.system_estimated_value = base_price * multiplier
        self.final_estimated_value = (
            (base_price * multiplier * Decimal('0.75')) +
            (self.user_estimated_value * Decimal('0.25'))
        )
        self.save()


# ---------------------------------------------------------------------------
# Listing photos (min 1, max 3 per listing)
# ---------------------------------------------------------------------------

class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='listings/')
    order = models.PositiveSmallIntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Photo {self.order} for {self.listing}"


# ---------------------------------------------------------------------------
# Saved listings
# ---------------------------------------------------------------------------

class SavedListing(models.Model):
    user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='saved_listings')
    listing = models.ForeignKey('Listing', on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['user', 'listing']]
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user} saved {self.listing}"


# ---------------------------------------------------------------------------
# Wishlist items
# ---------------------------------------------------------------------------

class WishlistItem(models.Model):
    user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='wishlist_items')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, blank=True)
    max_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    want_type = models.CharField(max_length=10, choices=WANT_TYPE_CHOICES, default='acquire')
    term_type = models.CharField(max_length=20, choices=TERM_TYPE_CHOICES, default='long_term')
    condition_acceptable = models.CharField(
        max_length=20, choices=CONDITION_ACCEPTABLE_CHOICES, default='any'
    )
    size_preference = models.CharField(max_length=50, blank=True)
    notification_frequency = models.CharField(
        max_length=10, choices=NOTIFICATION_FREQUENCY_CHOICES, default='instant'
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} wants {self.title}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            days = SiteSettings.get().wishlist_default_expiry_days
            self.expires_at = timezone.now() + timedelta(days=days)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Trade ratings
# ---------------------------------------------------------------------------

class TradeRating(models.Model):
    rater = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='ratings_given')
    rated_user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='ratings_received')
    offer = models.ForeignKey('Offer', on_delete=models.CASCADE, related_name='ratings')
    score = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['rater', 'offer']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rater} rated {self.rated_user}: {self.score}/5"


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(models.Model):
    user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.CharField(max_length=300)
    link = models.CharField(max_length=200, blank=True)
    match_tier = models.CharField(max_length=10, choices=MATCH_TIER_CHOICES, blank=True)
    is_read = models.BooleanField(default=False)
    clicked_at = models.DateTimeField(null=True, blank=True)
    source_listing = models.ForeignKey(
        'Listing', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='triggered_notifications',
    )
    source_wishlist_item = models.ForeignKey(
        'WishlistItem', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='triggered_notifications',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user}: {self.message[:60]}"


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

def _score_matches_with_ai(listing_title, listing_description, listing_category, candidates):
    """
    Batch-score candidates against a listing using OpenRouter (gpt-4o-mini).
    Returns list of dicts — id, score (0.0–1.0), reason. Empty list on failure.
    """
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key or not candidates:
        return []

    prompt = (
        'You are a matching engine for a barter marketplace in Ghana.\n\n'
        f'New listing:\n'
        f'- Title: {listing_title}\n'
        f'- Category: {listing_category}\n'
        f'- Description: {listing_description[:300]}\n\n'
        'Score each item below on how well it matches this listing (0.0–1.0). '
        'Score >= 0.90 for exact product-family match. '
        'Score 0.75–0.89 for strong same-category match. '
        'Score 0.55–0.74 for potential cross-category semantic match. '
        'Score < 0.55 for poor match.\n\n'
        'Items:\n'
        + _json.dumps([{
            'id': c['id'],
            'title': c['title'],
            'description': c.get('description', '')[:100],
            'category': c.get('category', ''),
        } for c in candidates])
        + '\n\nReturn ONLY valid JSON: {"matches": [{"id": <number>, "score": <0.0-1.0>, "reason": "<8 words max>"}]}'
    )

    try:
        resp = http_client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://barter.gh',
                'X-Title': 'Sesika',
            },
            json={
                'model': 'openai/gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        parsed = _json.loads(content)
        return parsed.get('matches', []) if isinstance(parsed, dict) else []
    except Exception:
        return []


def _score_to_tier(score: float) -> str:
    if score >= 0.90:
        return 'exact'
    if score >= 0.75:
        return 'strong'
    return 'potential'


def enrich_listing_with_ai(listing):
    """
    Generate AI-enriched context for a listing: attributes, tags, and value range.
    Stores result in listing.ai_enrichment. Does not overwrite admin-edited content.
    Called on admin approval alongside other AI steps.
    """
    if listing.ai_enrichment_admin_edited:
        return

    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return

    value_min = None
    value_max = None
    if listing.system_estimated_value:
        value_min = int(listing.system_estimated_value * Decimal('0.85'))
        value_max = int(listing.system_estimated_value * Decimal('1.15'))

    prompt = (
        'You are an AI assistant for Sesika, a Ghanaian barter marketplace.\n\n'
        f'Listing:\n'
        f'- Title: {listing.title}\n'
        f'- Category: {listing.get_category_display()}\n'
        f'- Condition: {listing.get_condition_display()}\n'
        f'- Description: {listing.description[:400]}\n\n'
        'Extract and infer structured details to help buyers understand this listing. '
        'Be concise. Use Ghanaian market context.\n\n'
        'Return ONLY valid JSON with these fields (omit fields you cannot determine):\n'
        '{"brand": "", "model": "", "key_specs": [], "condition_notes": "", '
        '"market_context": "", "tags": [], "value_source_note": "", '
        '"seo_title": "", "seo_description": ""}\n\n'
        'For seo_title: 50-70 chars, Google-optimised, include location if known, e.g. '
        '"Used iPhone 12 64GB — Trade or Swap in Accra, Ghana".\n'
        'For seo_description: 120-160 chars describing the listing for search result snippets.'
    )

    try:
        resp = http_client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://barter.gh',
                'X-Title': 'Sesika',
            },
            json={
                'model': 'openai/gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        enrichment = _json.loads(content)
    except Exception:
        enrichment = {}

    if value_min and value_max:
        enrichment['value_range_min'] = value_min
        enrichment['value_range_max'] = value_max
        source = listing.market_price.source if listing.market_price else 'category_baseline'
        enrichment['value_source'] = source

    seo_title = enrichment.pop('seo_title', '')[:70]
    seo_description = enrichment.pop('seo_description', '')[:160]
    listing.ai_enrichment = enrichment
    update_fields = ['ai_enrichment']
    if seo_title and not listing.seo_title:
        listing.seo_title = seo_title
        update_fields.append('seo_title')
    if seo_description and not listing.seo_description:
        listing.seo_description = seo_description
        update_fields.append('seo_description')
    listing.save(update_fields=update_fields)


def validate_and_correct_listing_category(listing):
    """
    Use OpenRouter to verify and auto-correct a listing's category and subcategory.
    Only writes changes if confidence >= 0.85 and category/subcategory differs.
    """
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return None

    active_cats = get_active_categories()
    sub_map = get_subcategory_map()
    category_map = _json.dumps({
        slug: {
            'label': label,
            'subcategories': {s: l for s, l in sub_map.get(slug, [])},
        }
        for slug, label in active_cats
    }, indent=2)

    prompt = (
        'You are a product categorization assistant for Sesika, a Ghanaian barter marketplace.\n\n'
        f'Listing to review:\n'
        f'- Title: {listing.title}\n'
        f'- Description: {listing.description[:400]}\n'
        f'- Current category: {listing.category}\n'
        f'- Current subcategory: {listing.subcategory}\n\n'
        f'Available categories and subcategories:\n{category_map}\n\n'
        'If the current category or subcategory is wrong, return the correct slugs. '
        'Only mark corrected=true if you are highly confident (0.85+). '
        'Return ONLY valid JSON:\n'
        '{"category": "<slug>", "subcategory": "<slug>", "confidence": <0.0-1.0>, "corrected": <true|false>}'
    )

    try:
        resp = http_client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://barter.gh',
                'X-Title': 'Sesika',
            },
            json={
                'model': 'openai/gpt-4o-mini',
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        result = _json.loads(content)
    except Exception:
        return None

    if not result.get('corrected') or result.get('confidence', 0) < 0.85:
        return None

    new_cat = result.get('category', '').strip()
    new_sub = result.get('subcategory', '').strip()

    valid_cats = {slug for slug, _ in active_cats}
    valid_subs = {slug for subs in sub_map.values() for slug, _ in subs}

    if new_cat not in valid_cats:
        return None
    if new_sub and new_sub not in valid_subs:
        new_sub = listing.subcategory

    if new_cat == listing.category and new_sub == listing.subcategory:
        return None

    old_cat = listing.category
    old_sub = listing.subcategory
    listing.category = new_cat
    listing.subcategory = new_sub
    listing.save(update_fields=['category', 'subcategory'])

    parts = []
    if new_cat != old_cat:
        parts.append(f'category {old_cat!r} → {new_cat!r}')
    if new_sub != old_sub:
        parts.append(f'subcategory {old_sub!r} → {new_sub!r}')
    return f'"{listing.title}": {", ".join(parts)}'


def count_wishlist_demand(listing):
    """
    Fast token-based count of active wishlist items that could match this listing.
    Respects transaction_type: trade listings only count acquire/either wants.
    """
    from django.db.models import Q
    tokens = {t for t in normalize_item_key(listing.title).split() if len(t) > 2}
    if not tokens:
        return 0

    wishlist_qs = WishlistItem.objects.filter(is_active=True).exclude(user=listing.user)

    if listing.transaction_type == 'trade':
        wishlist_qs = wishlist_qs.filter(want_type__in=['acquire', 'either'])
    elif listing.transaction_type == 'rental':
        wishlist_qs = wishlist_qs.filter(want_type__in=['rent', 'either'])

    if listing.category:
        wishlist_qs = wishlist_qs.filter(Q(category=listing.category) | Q(category=''))

    count = 0
    for item in wishlist_qs:
        item_tokens = {t for t in normalize_item_key(item.title).split() if len(t) > 2}
        if tokens & item_tokens:
            count += 1
    return count


def match_listing_to_wishlists(listing):
    """
    Two-stage AI matching: find wishlist items that match a listing, notify their owners.
    Respects transaction_type, want_type, and condition_acceptable.
    Returns notification count.
    """
    from django.db.models import Q

    tokens = {t for t in normalize_item_key(listing.title).split() if len(t) > 2}
    if not tokens:
        return 0

    wishlist_qs = WishlistItem.objects.filter(is_active=True).exclude(user=listing.user)

    if listing.transaction_type == 'trade':
        wishlist_qs = wishlist_qs.filter(want_type__in=['acquire', 'either'])
    elif listing.transaction_type == 'rental':
        wishlist_qs = wishlist_qs.filter(want_type__in=['rent', 'either'])

    if listing.category:
        wishlist_qs = wishlist_qs.filter(Q(category=listing.category) | Q(category=''))

    listing_condition_order = CONDITION_ORDER.get(listing.condition, 99)

    candidates = []
    for item in wishlist_qs:
        item_tokens = {t for t in normalize_item_key(item.title).split() if len(t) > 2}
        if not (tokens & item_tokens):
            continue
        if item.condition_acceptable and item.condition_acceptable != 'any':
            acceptable_order = CONDITION_ORDER.get(item.condition_acceptable, 99)
            if listing_condition_order > acceptable_order:
                continue
        candidates.append(item)
        if len(candidates) == 20:
            break

    if not candidates:
        return 0

    scored = _score_matches_with_ai(
        listing.title,
        listing.description,
        listing.get_category_display(),
        [{'id': c.pk, 'title': c.title, 'description': c.description,
          'category': c.get_category_display() if c.category else ''} for c in candidates],
    )
    score_map = {r['id']: r.get('score', 0) for r in scored} if scored else {c.pk: 0.75 for c in candidates}

    tolerance = Decimal(str(SiteSettings.get().budget_tolerance_pct)) / 100
    notified = 0

    for item in candidates:
        score = score_map.get(item.pk, 0)
        if score < 0.55:
            continue

        if item.max_budget and listing.final_estimated_value:
            max_allowed = item.max_budget * (Decimal('1') + tolerance)
            if listing.final_estimated_value > max_allowed:
                continue

        if Notification.objects.filter(
            source_listing=listing,
            source_wishlist_item=item,
            type='wishlist_match',
        ).exists():
            continue

        tier = _score_to_tier(score)
        budget_note = ''
        if item.max_budget and listing.final_estimated_value and listing.final_estimated_value > item.max_budget:
            budget_note = ' (slightly above your budget)'

        tier_label = {'exact': 'Exact match', 'strong': 'Strong match', 'potential': 'Possible match'}[tier]
        Notification.objects.create(
            user=item.user,
            type='wishlist_match',
            message=f'{tier_label}: "{listing.title}" matches your wishlist for "{item.title}"{budget_note}',
            link=f'/listings/{listing.pk}/',
            match_tier=tier,
            source_listing=listing,
            source_wishlist_item=item,
        )
        notified += 1

    return notified


def match_want_text_to_listings(listing):
    """
    Two-sided matching: find active listings that match what this listing's seller wants,
    and notify those listing owners of a potential trade opportunity.
    """
    if not listing.want_text:
        return

    want_tokens = {t for t in normalize_item_key(listing.want_text).split() if len(t) > 2}
    cash_noise = {'cash', 'money', 'ghs', 'cedis', 'cedi', 'and', 'for', 'the', 'any', 'or'}
    want_tokens -= cash_noise
    if not want_tokens:
        return

    active_listings = (
        Listing.objects.filter(status='active')
        .exclude(user=listing.user)
        .select_related('user')
    )

    candidates = []
    for active in active_listings:
        active_tokens = {t for t in normalize_item_key(active.title).split() if len(t) > 2}
        if want_tokens & active_tokens:
            candidates.append(active)
            if len(candidates) == 20:
                break

    if not candidates:
        return

    scored = _score_matches_with_ai(
        listing.want_text,
        f'Seller listed "{listing.title}" and wants: {listing.want_text}',
        listing.get_category_display(),
        [{'id': c.pk, 'title': c.title, 'description': c.description[:100],
          'category': c.get_category_display()} for c in candidates],
    )
    score_map = {r['id']: r.get('score', 0) for r in scored} if scored else {c.pk: 0.75 for c in candidates}

    for active in candidates:
        if score_map.get(active.pk, 0) < 0.55:
            continue

        if Notification.objects.filter(
            source_listing=listing,
            user=active.user,
            type='trade_opportunity',
        ).exists():
            continue

        Notification.objects.create(
            user=active.user,
            type='trade_opportunity',
            message=(
                f'Someone listed a "{listing.title}" and is looking for something like '
                f'your "{active.title}". They might want to trade!'
            ),
            link=f'/listings/{listing.pk}/',
            source_listing=listing,
        )


# ---------------------------------------------------------------------------
# Offer
# ---------------------------------------------------------------------------

OFFER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('countered', 'Countered'),
    ('accepted', 'Accepted'),
    ('rejected', 'Rejected'),
]


class Offer(models.Model):
    from_user = models.ForeignKey(
        BarterUser, on_delete=models.CASCADE, related_name='offers_made'
    )
    to_user = models.ForeignKey(
        BarterUser, on_delete=models.CASCADE, related_name='offers_received'
    )
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name='offers'
    )
    offer_type = models.CharField(max_length=10, choices=OFFER_TYPE_CHOICES, default='trade')
    offered_item_description = models.TextField(
        blank=True, help_text='Describe what you are offering in return'
    )
    cash_topup = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00')
    )
    suggested_cash_topup_min = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    suggested_cash_topup_max = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    message = models.TextField(blank=True)
    # Rental-specific
    rental_start_date = models.DateField(null=True, blank=True)
    rental_end_date = models.DateField(null=True, blank=True)
    rental_payment_offered = models.TextField(blank=True)
    # Counteroffer (set by listing owner)
    counter_cash_topup = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Cash top-up amount the seller is requesting as a counteroffer.',
    )
    counter_message = models.TextField(blank=True)
    # Status
    status = models.CharField(
        max_length=20, choices=OFFER_STATUS_CHOICES, default='pending'
    )
    contact_revealed = models.BooleanField(default=False)
    pending_timeout_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Offer by {self.from_user} on '{self.listing}'"

    def compute_suggested_topup(self, offered_value: Decimal):
        target = self.listing.final_estimated_value or self.listing.user_estimated_value
        diff = target - offered_value
        if diff < 0:
            diff = Decimal('0')
        self.suggested_cash_topup_min = (diff * Decimal('0.8')).quantize(Decimal('0.01'))
        self.suggested_cash_topup_max = (diff * Decimal('1.2')).quantize(Decimal('0.01'))

    def whatsapp_link(self):
        number = self.to_user.display_whatsapp.lstrip('+').replace(' ', '')
        lines = [f"Hi, I made an offer on your Sesika listing: *{self.listing.title}*"]
        if self.offered_item_description:
            lines.append(f"Item I'm offering: {self.offered_item_description}")
        if self.cash_topup:
            lines.append(f"Cash top-up: GHS {self.cash_topup:.2f}")
        if self.offer_type == 'rental':
            if self.rental_start_date and self.rental_end_date:
                lines.append(f"Rental period: {self.rental_start_date} to {self.rental_end_date}")
            if self.rental_payment_offered:
                lines.append(f"Payment offered: {self.rental_payment_offered}")
        if self.message:
            lines.append(f"Message: {self.message}")
        lines.append("Are you interested?")
        text = "\n".join(lines)
        return f"https://wa.me/{number}?text={urllib.parse.quote(text)}"


# ---------------------------------------------------------------------------
# Category cache invalidation signals
# ---------------------------------------------------------------------------

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver([post_save, post_delete], sender=Category)
def _invalidate_on_category_change(sender, **kwargs):
    invalidate_category_cache()


@receiver([post_save, post_delete], sender=Subcategory)
def _invalidate_on_subcategory_change(sender, **kwargs):
    invalidate_category_cache()


# ---------------------------------------------------------------------------
# Device tokens
# ---------------------------------------------------------------------------

class DeviceToken(models.Model):
    user = models.ForeignKey(
        BarterUser, on_delete=models.CASCADE, related_name='device_tokens'
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_seen']

    def __str__(self):
        return f"{self.user.phone} — {str(self.token)[:8]}… (last seen {self.last_seen:%Y-%m-%d})"


# ---------------------------------------------------------------------------
# Login attempts
# ---------------------------------------------------------------------------

class LoginAttempt(models.Model):
    phone = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        status = 'OK' if self.success else 'FAIL'
        return f"{self.phone} [{status}] {self.timestamp:%Y-%m-%d %H:%M}"
