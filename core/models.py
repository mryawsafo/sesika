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
    ('neither', 'No cash top-up'),
    ('open', 'Willing to pay or receive a top-up'),
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


def get_category_label(slug: str) -> str:
    if not slug:
        return ''
    for s, label in get_active_categories():
        if s == slug:
            return label
    return slug


# ---------------------------------------------------------------------------
# Category-specific attribute schemas
# ---------------------------------------------------------------------------

CATEGORY_ATTRIBUTE_SCHEMAS = {

    # ── Phones & Tablets ────────────────────────────────────────────────────
    'phones_tablets': {
        'form_sections': [
            {
                'section_id': 'device_identity',
                'label': 'Device Details',
                'transaction_types': None,
                'subcategory_exclude': ['phone_accessories'],
                'fields': [
                    {'name': 'storage_gb', 'label': 'Storage', 'type': 'select', 'required': True,
                     'options': [['16','16 GB'],['32','32 GB'],['64','64 GB'],['128','128 GB'],['256','256 GB'],['512','512 GB'],['1024','1 TB']]},
                    {'name': 'ram_gb', 'label': 'RAM', 'type': 'select', 'required': False,
                     'options': [['2','2 GB'],['3','3 GB'],['4','4 GB'],['6','6 GB'],['8','8 GB'],['12','12 GB'],['16','16 GB']]},
                    {'name': 'sim_slots', 'label': 'SIM Slots', 'type': 'select', 'required': False,
                     'options': [['no_sim','No SIM slot'],['single','Single SIM'],['dual','Dual SIM']]},
                ],
            },
            {
                'section_id': 'accessory_details',
                'label': 'Accessory Details',
                'transaction_types': None,
                'subcategory_types': ['phone_accessories'],
                'fields': [
                    {'name': 'accessory_type', 'label': 'Accessory Type', 'type': 'select', 'required': True,
                     'options': [['case','Phone Case / Cover'],['screen_protector','Screen Protector'],
                                 ['charger','Charger / Charging Cable'],['earphones','Earphones / Headphones'],
                                 ['power_bank','Power Bank'],['holder','Phone Holder / Stand'],
                                 ['memory_card','Memory Card'],['other','Other']]},
                    {'name': 'compatibility', 'label': 'Compatible with', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. iPhone 14, Samsung S22, Universal'},
                    {'name': 'connectivity', 'label': 'Connectivity', 'type': 'select', 'required': False,
                     'options': [['usb_c','USB-C'],['lightning','Lightning (Apple)'],['micro_usb','Micro-USB'],
                                 ['bluetooth','Bluetooth'],['wireless','Wireless'],['na','Not applicable']]},
                ],
            },
            {
                'section_id': 'condition_accessories',
                'label': 'Condition & Accessories',
                'transaction_types': None,
                'subcategory_exclude': ['phone_accessories'],
                'fields': [
                    {'name': 'battery_health', 'label': 'Battery Health (%)', 'type': 'number', 'required': False,
                     'min': 1, 'max': 100, 'placeholder': 'e.g. 87 — iPhones: Settings › Battery'},
                    {'name': 'screen_condition', 'label': 'Screen Condition', 'type': 'select', 'required': False,
                     'options': [['perfect','Perfect — no scratches'],['minor','Minor scratches (not visible in use)'],
                                 ['visible','Visible scratches / scuffs'],['cracked','Cracked screen']]},
                    {'name': 'body_condition', 'label': 'Body / Frame Condition', 'type': 'select', 'required': False,
                     'options': [['mint','Mint — no marks'],['minor_dents','Minor dents or scratches'],
                                 ['visible_damage','Visible damage'],['bent_broken','Bent or broken frame']]},
                    {'name': 'original_box', 'label': 'Original box included', 'type': 'checkbox', 'required': False},
                    {'name': 'charger_included', 'label': 'Charger / cable included', 'type': 'checkbox', 'required': False},
                    {'name': 'earphones_included', 'label': 'Earphones included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'sale_details',
                'label': 'Sale Details',
                'transaction_types': ['trade'],
                'subcategory_exclude': ['phone_accessories'],
                'fields': [
                    {'name': 'network_locked', 'label': 'Network Lock', 'type': 'select', 'required': False,
                     'options': [['unlocked','Unlocked (works on any network)'],['mtn','Locked to MTN'],
                                 ['vodafone','Locked to Vodafone'],['airteltigo','Locked to AirtelTigo']]},
                    {'name': 'icloud_removed', 'label': 'iCloud / Google account removed', 'type': 'checkbox', 'required': False},
                    {'name': 'warranty_remaining', 'label': 'Warranty remaining', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 6 months, Expired'},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Terms',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'weekly_price', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'sim_included', 'label': 'Local SIM card included', 'type': 'checkbox', 'required': False},
                    {'name': 'data_plan_included', 'label': 'Data plan included', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0,
                     'placeholder': 'e.g. 500'},
                ],
            },
        ],
    },

    # ── Computers & Laptops ─────────────────────────────────────────────────
    'computers': {
        'form_sections': [
            {
                'section_id': 'hardware_specs',
                'label': 'Hardware Specifications',
                'transaction_types': None,
                'subcategory_exclude': ['computer_accessories'],
                'fields': [
                    {'name': 'processor', 'label': 'Processor', 'type': 'select', 'required': True,
                     'options': [['intel_i3','Intel Core i3'],['intel_i5','Intel Core i5'],['intel_i7','Intel Core i7'],
                                 ['intel_i9','Intel Core i9'],['amd_ryzen5','AMD Ryzen 5'],['amd_ryzen7','AMD Ryzen 7'],
                                 ['apple_m1','Apple M1'],['apple_m2','Apple M2'],['apple_m3','Apple M3'],['apple_m4','Apple M4'],['other','Other']]},
                    {'name': 'ram_gb', 'label': 'RAM', 'type': 'select', 'required': True,
                     'options': [['4','4 GB'],['8','8 GB'],['12','12 GB'],['16','16 GB'],['32','32 GB'],['64','64 GB']]},
                    {'name': 'storage_gb', 'label': 'Storage Size', 'type': 'select', 'required': True,
                     'options': [['128','128 GB'],['256','256 GB'],['512','512 GB'],['1000','1 TB'],['2000','2 TB']]},
                    {'name': 'storage_type', 'label': 'Storage Type', 'type': 'select', 'required': False,
                     'options': [['ssd','SSD'],['hdd','HDD'],['ssd_hdd','SSD + HDD']]},
                    {'name': 'screen_size', 'label': 'Screen Size (inches)', 'type': 'select', 'required': False,
                     'options': [['11','11"'],['13','13"'],['14','14"'],['15','15.6"'],['16','16"'],['17','17"']]},
                    {'name': 'gpu', 'label': 'Dedicated GPU', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. NVIDIA RTX 3060, AMD Radeon — blank if integrated only'},
                ],
            },
            {
                'section_id': 'condition_accessories',
                'label': 'Condition & Accessories',
                'transaction_types': None,
                'subcategory_exclude': ['computer_accessories'],
                'fields': [
                    {'name': 'battery_health', 'label': 'Battery Health (%)', 'type': 'number', 'required': False,
                     'min': 1, 'max': 100, 'placeholder': 'e.g. 82'},
                    {'name': 'screen_condition', 'label': 'Screen Condition', 'type': 'select', 'required': False,
                     'options': [['perfect','Perfect — no marks or dead pixels'],['minor_scratches','Minor scratches (not visible in use)'],
                                 ['visible_marks','Visible marks or blemishes'],['cracked','Cracked or damaged']]},
                    {'name': 'charger_included', 'label': 'Charger included', 'type': 'checkbox', 'required': False},
                    {'name': 'touch_screen', 'label': 'Touchscreen', 'type': 'checkbox', 'required': False},
                    {'name': 'original_box', 'label': 'Original box included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'sale_details',
                'label': 'Sale Details',
                'transaction_types': ['trade'],
                'subcategory_exclude': ['computer_accessories'],
                'fields': [
                    {'name': 'os', 'label': 'Operating System', 'type': 'select', 'required': False,
                     'options': [['windows11','Windows 11'],['windows10','Windows 10'],['macos','macOS'],
                                 ['linux','Linux'],['chromeos','Chrome OS'],['no_os','No OS installed']]},
                    {'name': 'windows_licence', 'label': 'Genuine Windows licence included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'computer_accessory_details',
                'label': 'Accessory Details',
                'transaction_types': None,
                'subcategory_types': ['computer_accessories'],
                'fields': [
                    {'name': 'accessory_type', 'label': 'Accessory Type', 'type': 'select', 'required': True,
                     'options': [['keyboard','Keyboard'],['mouse','Mouse'],['monitor','External Monitor'],
                                 ['webcam','Webcam'],['headset','Headset / Headphones'],['charger','Charger / Adapter'],
                                 ['hub','USB Hub / Docking Station'],['bag','Laptop Bag / Case'],
                                 ['memory','RAM / Storage Upgrade'],['cable','Cable / Adapter'],['other','Other']]},
                    {'name': 'compatibility', 'label': 'Compatible with', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. MacBook Pro, any USB-C laptop, Windows only'},
                    {'name': 'connectivity', 'label': 'Connectivity', 'type': 'select', 'required': False,
                     'options': [['usb_a','USB-A'],['usb_c','USB-C'],['thunderbolt','Thunderbolt'],
                                 ['bluetooth','Bluetooth'],['wireless','2.4 GHz Wireless'],['hdmi','HDMI'],['na','Not applicable']]},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Setup',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'preloaded_software', 'label': 'Preloaded software', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. MS Office, Adobe CC, AutoCAD'},
                    {'name': 'os_fresh_install', 'label': 'Fresh OS install between rentals', 'type': 'checkbox', 'required': False},
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'weekly_price', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0,
                     'placeholder': 'e.g. 1000'},
                ],
            },
        ],
    },

    # ── Electronics ─────────────────────────────────────────────────────────
    'electronics': {
        'form_sections': [
            {
                'section_id': 'tv_details',
                'label': 'TV & Display Details',
                'transaction_types': None,
                'subcategory_types': ['tvs'],
                'fields': [
                    {'name': 'screen_size', 'label': 'Screen Size (inches)', 'type': 'number', 'required': True,
                     'min': 10, 'max': 120, 'placeholder': 'e.g. 43'},
                    {'name': 'display_technology', 'label': 'Display Technology', 'type': 'select', 'required': False,
                     'options': [['led','LED'],['qled','QLED'],['oled','OLED'],['nanocell','NanoCell / Mini LED'],
                                 ['lcd','LCD'],['other','Other']]},
                    {'name': 'resolution', 'label': 'Resolution', 'type': 'select', 'required': False,
                     'options': [['hd','HD 720p'],['fhd','Full HD 1080p'],['4k','4K UHD'],['8k','8K']]},
                    {'name': 'smart', 'label': 'Smart TV / WiFi enabled', 'type': 'checkbox', 'required': False},
                    {'name': 'remote_included', 'label': 'Remote control included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'audio_details',
                'label': 'Audio Details',
                'transaction_types': None,
                'subcategory_types': ['audio'],
                'fields': [
                    {'name': 'audio_type', 'label': 'Type', 'type': 'select', 'required': True,
                     'options': [['speaker','Speaker / Sound system'],['soundbar','Soundbar'],
                                 ['home_theatre','Home Theatre System'],['headphones','Headphones / Earphones'],
                                 ['amplifier','Amplifier / Receiver'],['subwoofer','Subwoofer'],['other','Other']]},
                    {'name': 'power_output_watts', 'label': 'Power Output (Watts)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 100'},
                    {'name': 'wireless', 'label': 'Bluetooth / Wireless', 'type': 'checkbox', 'required': False},
                    {'name': 'cables_included', 'label': 'Cables / adapters included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'camera_details',
                'label': 'Camera Details',
                'transaction_types': None,
                'subcategory_types': ['cameras'],
                'fields': [
                    {'name': 'camera_type', 'label': 'Camera Type', 'type': 'select', 'required': True,
                     'options': [['dslr','DSLR'],['mirrorless','Mirrorless'],['point_shoot','Point & Shoot'],
                                 ['action','Action Camera (GoPro etc.)'],['security','Security / CCTV'],['other','Other']]},
                    {'name': 'megapixels', 'label': 'Megapixels', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 24'},
                    {'name': 'lens_included', 'label': 'Lens(es) included', 'type': 'checkbox', 'required': False},
                    {'name': 'memory_card_included', 'label': 'Memory card included', 'type': 'checkbox', 'required': False},
                    {'name': 'bag_included', 'label': 'Camera bag / case included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'smart_watch_details',
                'label': 'Smart Watch Details',
                'transaction_types': None,
                'subcategory_types': ['smart_watches'],
                'fields': [
                    {'name': 'compatibility', 'label': 'Compatible with', 'type': 'select', 'required': False,
                     'options': [['ios','iOS (iPhone)'],['android','Android'],['both','iOS & Android'],
                                 ['independent','Works independently']]},
                    {'name': 'strap_material', 'label': 'Strap Material', 'type': 'select', 'required': False,
                     'options': [['silicone','Silicone'],['leather','Leather'],['metal','Metal / Stainless'],
                                 ['nylon','Nylon / Fabric'],['other','Other']]},
                    {'name': 'gps', 'label': 'Built-in GPS', 'type': 'checkbox', 'required': False},
                    {'name': 'waterproof', 'label': 'Water resistant / waterproof', 'type': 'checkbox', 'required': False},
                    {'name': 'original_box', 'label': 'Original box & charger included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'other_electronics_details',
                'label': 'Product Details',
                'transaction_types': None,
                'subcategory_types': ['other_electronics'],
                'fields': [
                    {'name': 'item_type', 'label': 'Item Type', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Printer, Router, Decoder, Projector'},
                    {'name': 'cables_included', 'label': 'Cables / accessories included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'condition',
                'label': 'Condition & Documentation',
                'transaction_types': None,
                'fields': [
                    {'name': 'warranty_remaining', 'label': 'Warranty remaining', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 8 months, Expired'},
                    {'name': 'receipt_available', 'label': 'Receipt / proof of purchase available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Logistics',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'quantity_available', 'label': 'Units available', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 2 speakers, 1 projector'},
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'delivery_included', 'label': 'Delivery & collection included', 'type': 'checkbox', 'required': False},
                    {'name': 'setup_included', 'label': 'Setup & testing included', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                ],
            },
        ],
    },

    # ── Gaming ──────────────────────────────────────────────────────────────
    'gaming': {
        'form_sections': [
            {
                'section_id': 'console_details',
                'label': 'Console Details',
                'transaction_types': None,
                'subcategory_exclude': ['games', 'gaming_accessories', 'pc_parts'],
                'fields': [
                    {'name': 'platform', 'label': 'Platform', 'type': 'select', 'required': True,
                     'options': [['ps5','PlayStation 5'],['ps4','PlayStation 4'],['ps3','PlayStation 3'],
                                 ['xbox_series','Xbox Series X/S'],['xbox_one','Xbox One'],
                                 ['nintendo_switch','Nintendo Switch'],['pc','PC / Steam Deck'],['other','Other']]},
                    {'name': 'storage_gb', 'label': 'Console Storage', 'type': 'select', 'required': False,
                     'options': [['500','500 GB'],['825','825 GB'],['1000','1 TB'],['2000','2 TB']]},
                    {'name': 'form_factor', 'label': 'Form Factor', 'type': 'select', 'required': False,
                     'options': [['home','Home Console'],['handheld','Handheld'],['hybrid','Hybrid (e.g. Switch)']]},
                    {'name': 'disc_drive', 'label': 'Disc Drive included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'console_bundle',
                'label': 'Accessories & Games Included',
                'transaction_types': None,
                'subcategory_exclude': ['games', 'gaming_accessories', 'pc_parts'],
                'fields': [
                    {'name': 'controllers', 'label': 'Controllers included', 'type': 'number', 'required': False,
                     'min': 0, 'max': 8, 'placeholder': 'e.g. 2'},
                    {'name': 'headset_included', 'label': 'Headset included', 'type': 'checkbox', 'required': False},
                    {'name': 'game_titles', 'label': 'Games included', 'type': 'textarea', 'required': False,
                     'placeholder': 'e.g. FIFA 25, GTA V, God of War'},
                ],
            },
            {
                'section_id': 'games_details',
                'label': 'Game Details',
                'transaction_types': None,
                'subcategory_types': ['games'],
                'fields': [
                    {'name': 'platform', 'label': 'Platform', 'type': 'select', 'required': True,
                     'options': [['ps5','PlayStation 5'],['ps4','PlayStation 4'],['ps3','PlayStation 3'],
                                 ['xbox_series','Xbox Series X/S'],['xbox_one','Xbox One'],
                                 ['nintendo_switch','Nintendo Switch'],['pc','PC'],['other','Other']]},
                    {'name': 'genre', 'label': 'Genre', 'type': 'select', 'required': False,
                     'options': [['action','Action'],['adventure','Adventure'],['sports','Sports'],
                                 ['racing','Racing'],['shooting','Shooter / FPS'],['rpg','RPG'],
                                 ['fighting','Fighting'],['simulation','Simulation'],['strategy','Strategy'],
                                 ['horror','Horror'],['arcade','Arcade'],['other','Other']]},
                    {'name': 'age_rating', 'label': 'Age Rating', 'type': 'select', 'required': False,
                     'options': [['e','E — Everyone'],['e10','E10+ — Everyone 10+'],['t','T — Teen'],
                                 ['m','M — Mature 17+'],['ao','AO — Adults Only']]},
                    {'name': 'release_year', 'label': 'Release Year', 'type': 'number', 'required': False,
                     'min': 1990, 'max': 2026, 'placeholder': 'e.g. 2023'},
                    {'name': 'format', 'label': 'Format', 'type': 'select', 'required': False,
                     'options': [['disc','Physical Disc'],['digital','Digital Code'],['both','Disc + Digital']]},
                ],
            },
            {
                'section_id': 'gaming_accessories_details',
                'label': 'Accessory Details',
                'transaction_types': None,
                'subcategory_types': ['gaming_accessories'],
                'fields': [
                    {'name': 'accessory_type', 'label': 'Accessory Type', 'type': 'select', 'required': True,
                     'options': [['controller','Controller / Gamepad'],['headset','Gaming Headset'],
                                 ['steering','Steering Wheel / Racing setup'],['vr','VR Headset'],
                                 ['keyboard','Gaming Keyboard'],['mouse','Gaming Mouse'],
                                 ['monitor','Gaming Monitor'],['chair','Gaming Chair'],
                                 ['charger','Charging Dock / Cable'],['other','Other']]},
                    {'name': 'compatibility', 'label': 'Compatible with', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. PS5, Xbox Series X, PC, Universal'},
                ],
            },
            {
                'section_id': 'pc_parts_details',
                'label': 'PC Part Details',
                'transaction_types': None,
                'subcategory_types': ['pc_parts'],
                'fields': [
                    {'name': 'component_type', 'label': 'Component Type', 'type': 'select', 'required': True,
                     'options': [['gpu','Graphics Card (GPU)'],['cpu','Processor (CPU)'],['ram','RAM'],
                                 ['motherboard','Motherboard'],['psu','Power Supply (PSU)'],
                                 ['cooling','Cooling (Fan / AIO)'],['case','PC Case'],['other','Other']]},
                    {'name': 'brand_model', 'label': 'Brand & Model', 'type': 'text', 'required': True,
                     'placeholder': 'e.g. RTX 3060 Ti, Ryzen 5 5600X, Corsair 16GB DDR4'},
                    {'name': 'socket_compatibility', 'label': 'Socket / Compatibility', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. LGA1700, AM5, DDR4'},
                ],
            },
            {
                'section_id': 'sale_details',
                'label': 'Sale Details',
                'transaction_types': ['trade'],
                'subcategory_exclude': ['games', 'gaming_accessories', 'pc_parts'],
                'fields': [
                    {'name': 'account_unlinked', 'label': 'PSN / Xbox / Nintendo account unlinked', 'type': 'checkbox', 'required': False},
                    {'name': 'original_box', 'label': 'Original box included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Setup',
                'transaction_types': ['rental'],
                'subcategory_exclude': ['games', 'gaming_accessories', 'pc_parts'],
                'fields': [
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'per_event_price', 'label': 'Party / event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'setup_included', 'label': 'Setup & teardown included', 'type': 'checkbox', 'required': False},
                    {'name': 'games_swappable', 'label': 'Renter can bring own games', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                ],
            },
        ],
    },

    # ── Vehicles ────────────────────────────────────────────────────────────
    'vehicles': {
        'form_sections': [
            {
                'section_id': 'identity',
                'label': 'Vehicle Identity',
                'transaction_types': None,
                'fields': [
                    {'name': 'year', 'label': 'Year', 'type': 'number', 'required': True, 'min': 1960, 'max': 2026,
                     'placeholder': 'e.g. 2010'},
                    {'name': 'make', 'label': 'Make', 'type': 'text', 'required': True,
                     'placeholder': 'e.g. Opel, Toyota, Hyundai'},
                    {'name': 'model', 'label': 'Model', 'type': 'text', 'required': True,
                     'placeholder': 'e.g. Combo, HiAce, H100'},
                    {'name': 'variant', 'label': 'Variant / Trim', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 1.6 CDTi, L2H1, Cargo'},
                    {'name': 'colour', 'label': 'Colour', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. White, Silver'},
                    {'name': 'body_type', 'label': 'Body Type', 'type': 'select', 'required': True,
                     'options': [['car','Car / Saloon'],['suv','SUV / 4x4'],['pickup','Pickup Truck'],
                                 ['panel_van','Panel Van (Cargo)'],['minivan','Minivan / Passenger Van'],
                                 ['crew_van','Crew Van'],['refrigerated','Refrigerated Van'],
                                 ['dropside','Dropside / Flatbed'],['minibus','Minibus'],['bus','Bus']]},
                ],
            },
            {
                'section_id': 'specs',
                'label': 'Technical Specifications',
                'transaction_types': None,
                'fields': [
                    {'name': 'engine_size_cc', 'label': 'Engine Size (cc)', 'type': 'number', 'required': False,
                     'min': 600, 'max': 8000, 'placeholder': 'e.g. 1600'},
                    {'name': 'fuel_type', 'label': 'Fuel Type', 'type': 'select', 'required': True,
                     'options': [['petrol','Petrol'],['diesel','Diesel'],['lpg','LPG'],['hybrid','Hybrid'],['electric','Electric']]},
                    {'name': 'transmission', 'label': 'Transmission', 'type': 'select', 'required': True,
                     'options': [['manual','Manual'],['automatic','Automatic'],['semi_auto','Semi-Automatic']]},
                    {'name': 'drivetrain', 'label': 'Drivetrain', 'type': 'select', 'required': False,
                     'options': [['fwd','Front-Wheel Drive'],['rwd','Rear-Wheel Drive'],['4wd','4WD'],['awd','AWD']]},
                    {'name': 'mileage_km', 'label': 'Mileage (km)', 'type': 'number', 'required': True,
                     'min': 0, 'placeholder': 'e.g. 145000'},
                    {'name': 'seating_capacity', 'label': 'Seating Capacity', 'type': 'number', 'required': False,
                     'min': 1, 'max': 100, 'placeholder': 'e.g. 2, 9, 14'},
                    {'name': 'cargo_volume_m3', 'label': 'Cargo Volume (m³)', 'type': 'number', 'required': False,
                     'min': 0, 'step': 0.1, 'placeholder': 'e.g. 3.4'},
                    {'name': 'payload_kg', 'label': 'Payload Capacity (kg)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 800'},
                    {'name': 'ac', 'label': 'Air Conditioning', 'type': 'checkbox', 'required': False},
                    {'name': 'power_steering', 'label': 'Power Steering', 'type': 'checkbox', 'required': False},
                    {'name': 'abs', 'label': 'ABS Brakes', 'type': 'checkbox', 'required': False},
                    {'name': 'reverse_camera', 'label': 'Reverse Camera', 'type': 'checkbox', 'required': False},
                    {'name': 'roof_rack', 'label': 'Roof Rack', 'type': 'checkbox', 'required': False},
                    {'name': 'tow_hitch', 'label': 'Tow Hitch / Trailer Hook', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'condition',
                'label': 'Condition & History',
                'transaction_types': None,
                'fields': [
                    {'name': 'overall_condition', 'label': 'Overall Condition', 'type': 'select', 'required': True,
                     'options': [['excellent','Excellent — near new'],['good','Good — minor wear'],
                                 ['fair','Fair — visible wear, fully functional'],['poor','Poor — needs attention'],
                                 ['project','Project — for parts or major repair']]},
                    {'name': 'accident_history', 'label': 'Accident History', 'type': 'select', 'required': True,
                     'options': [['none','No accidents'],['minor_repaired','Minor accident, repaired'],
                                 ['major_repaired','Major accident, repaired'],['salvage','Salvage title']]},
                    {'name': 'service_history', 'label': 'Service History', 'type': 'select', 'required': False,
                     'options': [['full','Full history (receipts available)'],['partial','Partial history'],
                                 ['none','No history / unknown']]},
                    {'name': 'last_service_date', 'label': 'Last Service Date', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. January 2024'},
                    {'name': 'known_defects', 'label': 'Known Defects or Issues', 'type': 'textarea', 'required': False,
                     'placeholder': 'e.g. AC not working, slight rust on rear door — honesty builds trust'},
                    {'name': 'roadworthy_status', 'label': 'Roadworthy / DVLA Status', 'type': 'select', 'required': True,
                     'options': [['current','Current certificate'],['expired','Expired — needs renewal'],
                                 ['not_roadworthy','Not roadworthy'],['unknown','Unknown']]},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Terms',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'daily_rate_ghs', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 350'},
                    {'name': 'weekly_rate_ghs', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 2000'},
                    {'name': 'monthly_rate_ghs', 'label': 'Monthly Rate (GHS)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 7500'},
                    {'name': 'driver_option', 'label': 'Driver', 'type': 'select', 'required': True,
                     'options': [['self_drive','Self-drive only'],['driver_included','Driver included in rate'],
                                 ['driver_extra','Driver available at extra cost']]},
                    {'name': 'fuel_policy', 'label': 'Fuel Policy', 'type': 'select', 'required': True,
                     'options': [['full_to_full','Full-to-full (renter refuels)'],['included','Fuel included in rate'],
                                 ['actual','Renter pays actual fuel used']]},
                    {'name': 'mileage_limit_km_day', 'label': 'Daily Mileage Limit (km)', 'type': 'number',
                     'required': False, 'min': 0, 'placeholder': 'e.g. 200 — blank for unlimited'},
                    {'name': 'deposit_amount_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number',
                     'required': False, 'min': 0, 'placeholder': 'e.g. 500'},
                    {'name': 'min_rental_days', 'label': 'Minimum Rental (days)', 'type': 'number',
                     'required': False, 'min': 1, 'placeholder': 'e.g. 1'},
                    {'name': 'advance_booking_days', 'label': 'Advance Booking Required (days)', 'type': 'number',
                     'required': False, 'min': 0, 'placeholder': 'e.g. 1'},
                ],
            },
            {
                'section_id': 'sale_details',
                'label': 'Sale Details',
                'transaction_types': ['trade'],
                'fields': [
                    {'name': 'negotiable', 'label': 'Price negotiable', 'type': 'checkbox', 'required': False},
                    {'name': 'reason_for_sale', 'label': 'Reason for Selling', 'type': 'select', 'required': False,
                     'options': [['upgrading','Upgrading'],['no_longer_needed','No longer needed'],
                                 ['financial','Financial reasons'],['fleet_reduction','Fleet reduction'],
                                 ['prefer_not','Prefer not to say']]},
                    {'name': 'viewing_available', 'label': 'Test drive / viewing available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'documentation',
                'label': 'Documentation',
                'transaction_types': None,
                'fields': [
                    {'name': 'registration_region', 'label': 'Registration Region', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Greater Accra, Ashanti'},
                    {'name': 'insurance_type', 'label': 'Insurance Type', 'type': 'select', 'required': False,
                     'options': [['comprehensive','Comprehensive'],['third_party','Third Party'],
                                 ['tpft','Third Party Fire & Theft'],['none','None / Expired']]},
                    {'name': 'roadworthy_expiry', 'label': 'Roadworthy Expiry', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. March 2026'},
                ],
            },
        ],
        'ai_extraction_fields': [
            {'name': 'normalized_title', 'description': '[Year] [Make] [Model] [body_type] – [transaction_type] in [location_city], Ghana'},
            {'name': 'feature_tags', 'description': 'diesel, manual, 145k km, AC, cargo van, roadworthy'},
            {'name': 'usage_vectors', 'description': 'logistics, airport transfers, moving, event transport, delivery'},
            {'name': 'price_estimate_range', 'description': 'Market value in GHS based on year, make, mileage, condition'},
            {'name': 'fraud_risk_score', 'description': 'Elevated by: no photos, price far below market, year/mileage mismatch'},
        ],
        'seo_fields': {
            'title_template': '{year} {make} {model} {body_type} – {transaction_type} in {location_city}, Ghana',
            'description_template': '{year} {make} {model} {transaction_type} in {location_city}. {fuel_type}, {transmission}, {mileage_km}km.',
            'keywords': ['{make} {model} for rent Ghana', 'van rental Ghana', '{body_type} hire {location_city}'],
        },
    },

    # ── Fashion ─────────────────────────────────────────────────────────────
    'fashion': {
        'form_sections': [
            {
                'section_id': 'clothing_details',
                'label': 'Item Details',
                'transaction_types': None,
                'subcategory_exclude': ['shoes', 'sneakers', 'bags_accessories', 'thrift'],
                'fields': [
                    {'name': 'garment_type', 'label': 'Type', 'type': 'select', 'required': False,
                     'options': [['dress','Dress'],['top','Top / T-Shirt / Blouse'],['shirt','Shirt'],
                                 ['jeans','Jeans / Trousers'],['shorts','Shorts'],['skirt','Skirt'],
                                 ['jacket','Jacket / Coat'],['suit','Suit / Blazer'],['joggers','Joggers / Tracksuit'],
                                 ['agbada','Agbada / Senator'],['kente','Kente / Traditional wear'],
                                 ['ankara','Ankara / Fabric'],['lingerie','Lingerie / Underwear'],
                                 ['activewear','Activewear / Sportswear'],['swimwear','Swimwear'],
                                 ['uniform','Uniform'],['other','Other']]},
                    {'name': 'size', 'label': 'Size', 'type': 'text', 'required': True,
                     'placeholder': 'e.g. M, L, XL, UK 10, EU 42, 32W/30L'},
                    {'name': 'colour', 'label': 'Colour', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Black, Navy Blue, Kente print'},
                    {'name': 'material', 'label': 'Material / Fabric', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 100% Cotton, Polyester blend, Kente'},
                    {'name': 'style_type', 'label': 'Style', 'type': 'select', 'required': False,
                     'options': [['casual','Casual / Everyday'],['formal','Formal / Corporate'],
                                 ['traditional','Traditional (Kente, Kaba, Batakari)'],['sportswear','Sportswear / Activewear'],
                                 ['wedding','Wedding / Bridal'],['vintage','Vintage / Thrift'],
                                 ['ethnic','Ethnic / Cultural'],['boho','Boho / Relaxed']]},
                ],
            },
            {
                'section_id': 'shoes_details',
                'label': 'Shoe Details',
                'transaction_types': None,
                'subcategory_types': ['shoes', 'sneakers'],
                'fields': [
                    {'name': 'shoe_type', 'label': 'Shoe Type', 'type': 'select', 'required': True,
                     'options': [['sneakers','Sneakers / Trainers'],['sandals','Sandals'],
                                 ['slippers','Slippers / Flip-flops'],['boots','Boots'],
                                 ['loafers','Loafers / Moccasins'],['heels','Heels'],
                                 ['flat','Flat Shoes / Ballerinas'],['football_boots','Football Boots'],
                                 ['safety','Safety / Work Boots'],['other','Other']]},
                    {'name': 'size', 'label': 'Size', 'type': 'text', 'required': True,
                     'placeholder': 'e.g. UK 9, EU 43, US 10'},
                    {'name': 'gender', 'label': 'For', 'type': 'select', 'required': False,
                     'options': [['women',"Women's"],['men',"Men's"],['unisex','Unisex'],
                                 ['girls',"Girls'"],['boys',"Boys'"]]},
                    {'name': 'colour', 'label': 'Colour', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. White, Black, Multicolour'},
                ],
            },
            {
                'section_id': 'bags_details',
                'label': 'Bag & Accessory Details',
                'transaction_types': None,
                'subcategory_types': ['bags_accessories'],
                'fields': [
                    {'name': 'bag_type', 'label': 'Type', 'type': 'select', 'required': True,
                     'options': [['handbag','Handbag'],['backpack','Backpack'],['tote','Tote Bag'],
                                 ['clutch','Clutch / Evening Bag'],['crossbody','Crossbody / Shoulder Bag'],
                                 ['wallet','Wallet / Purse'],['belt','Belt'],['hat','Hat / Cap'],
                                 ['jewellery','Jewellery'],['watch','Watch'],['sunglasses','Sunglasses'],['other','Other']]},
                    {'name': 'material', 'label': 'Material', 'type': 'select', 'required': False,
                     'options': [['leather','Leather'],['faux_leather','Faux Leather / PU'],['fabric','Fabric / Canvas'],
                                 ['suede','Suede'],['plastic','Plastic / Hard shell'],['other','Other']]},
                    {'name': 'colour', 'label': 'Colour', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Black, Tan, Brown'},
                    {'name': 'branded', 'label': 'Designer / Branded item', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'thrift_details',
                'label': 'Thrift Details',
                'transaction_types': None,
                'subcategory_types': ['thrift'],
                'fields': [
                    {'name': 'gender', 'label': 'For', 'type': 'select', 'required': False,
                     'options': [['women',"Women's"],['men',"Men's"],['unisex','Mixed / Unisex'],['kids',"Kids'"]]},
                    {'name': 'item_count', 'label': 'Number of pieces', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 1 (single item) or 10 (bundle)'},
                    {'name': 'size_range', 'label': 'Size Range', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. UK 10–14, Mixed sizes'},
                    {'name': 'era', 'label': 'Era / Style', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Y2K, 90s, Modern'},
                ],
            },
            {
                'section_id': 'condition',
                'label': 'Condition',
                'transaction_types': None,
                'fields': [
                    {'name': 'worn_count', 'label': 'Times worn', 'type': 'select', 'required': False,
                     'options': [['never','Never worn (with tags)'],['once','Worn once'],['few','Worn a few times'],
                                 ['regularly','Regularly worn'],['heavily','Heavily worn']]},
                    {'name': 'alterations_done', 'label': 'Any alterations made', 'type': 'checkbox', 'required': False},
                    {'name': 'stains_damage', 'label': 'Stains or visible damage', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. None, small stain on hem — be honest'},
                ],
            },
            {
                'section_id': 'sale_details',
                'label': 'Sale Details',
                'transaction_types': ['trade'],
                'subcategory_exclude': ['bags_accessories', 'thrift'],
                'fields': [
                    {'name': 'new_with_tags', 'label': 'New with tags (unworn)', 'type': 'checkbox', 'required': False},
                    {'name': 'original_packaging', 'label': 'Original packaging / box', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Terms',
                'transaction_types': ['rental'],
                'subcategory_exclude': ['shoes', 'sneakers', 'bags_accessories', 'thrift'],
                'fields': [
                    {'name': 'occasion', 'label': 'Best for', 'type': 'select', 'required': False,
                     'options': [['wedding','Wedding / Engagement'],['formal','Formal / Corporate event'],
                                 ['traditional','Traditional ceremony'],['party','Party / Night out'],
                                 ['costume','Costume / Themed event'],['casual','Casual occasion']]},
                    {'name': 'dry_cleaning_fee', 'label': 'Dry cleaning fee (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'per_day_price', 'label': 'Per-day Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0,
                     'placeholder': 'e.g. 200'},
                    {'name': 'dry_clean_before_handover', 'label': 'Dry-cleaned before each rental', 'type': 'checkbox', 'required': False},
                ],
            },
        ],
    },

    # ── Home & Furniture ────────────────────────────────────────────────────
    'home_furniture': {
        'form_sections': [
            {
                'section_id': 'furniture_details',
                'label': 'Furniture Details',
                'transaction_types': None,
                'subcategory_types': ['furniture'],
                'fields': [
                    {'name': 'item_type', 'label': 'Item Type', 'type': 'select', 'required': False,
                     'options': [['sofa','Sofa / Couch'],['armchair','Armchair'],['bed','Bed Frame'],
                                 ['mattress','Mattress'],['dining_set','Dining Table & Chairs'],
                                 ['wardrobe','Wardrobe / Closet'],['desk','Desk / Study Table'],
                                 ['chair','Chair / Stool'],['tv_stand','TV Stand'],
                                 ['bookcase','Bookcase / Shelving'],['cabinet','Cabinet / Cupboard'],
                                 ['dresser','Dresser / Dressing Table'],['other','Other']]},
                    {'name': 'material', 'label': 'Material', 'type': 'select', 'required': False,
                     'options': [['wood','Wood / Solid Wood'],['mdf','MDF / Chipboard'],['plywood','Plywood'],
                                 ['metal','Metal / Steel'],['glass','Glass'],['leather','Leather'],
                                 ['fabric','Fabric / Upholstered'],['rattan','Rattan / Wicker'],
                                 ['marble','Marble'],['plastic','Plastic'],['mixed','Mixed']]},
                    {'name': 'colour', 'label': 'Colour / Finish', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Brown, White, Oak finish'},
                    {'name': 'room', 'label': 'Room', 'type': 'select', 'required': False,
                     'options': [['living_room','Living Room'],['bedroom','Bedroom'],['dining_room','Dining Room'],
                                 ['kitchen','Kitchen'],['home_office','Home Office / Study'],
                                 ['bathroom','Bathroom'],['outdoor','Outdoor / Balcony / Patio'],
                                 ['playroom','Playroom'],['other','Other']]},
                    {'name': 'dimensions', 'label': 'Dimensions (L × W × H cm)', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 180 × 90 × 75'},
                    {'name': 'seating_capacity', 'label': 'Seating capacity', 'type': 'number', 'required': False,
                     'placeholder': 'e.g. 3 (sofas, dining sets)'},
                ],
            },
            {
                'section_id': 'appliances_details',
                'label': 'Appliance Details',
                'transaction_types': None,
                'subcategory_types': ['home_appliances'],
                'fields': [
                    {'name': 'appliance_type', 'label': 'Appliance Type', 'type': 'select', 'required': True,
                     'options': [['fridge','Refrigerator / Freezer'],['washing_machine','Washing Machine'],
                                 ['ac','Air Conditioner'],['microwave','Microwave'],['oven','Oven / Cooker / Stove'],
                                 ['water_heater','Water Heater'],['generator','Generator'],
                                 ['fan','Fan / Air Cooler'],['iron','Iron / Steamer'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. LG, Samsung, Hisense, Nasco, Bruhm'},
                    {'name': 'capacity', 'label': 'Capacity', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 300 L (fridge), 7 kg (washer), 1.5 HP (AC), 2.5 kVA (gen)'},
                    {'name': 'energy_rating', 'label': 'Energy Rating', 'type': 'select', 'required': False,
                     'options': [['a_plus','A+ (Most efficient)'],['a','A'],['b','B'],['c','C or below'],['unknown','Unknown']]},
                    {'name': 'installation_required', 'label': 'Professional installation required', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'kitchen_details',
                'label': 'Kitchen & Dining Details',
                'transaction_types': None,
                'subcategory_types': ['kitchen'],
                'fields': [
                    {'name': 'kitchen_item_type', 'label': 'Item Type', 'type': 'select', 'required': False,
                     'options': [['pots_pans','Pots & Pans / Cookware Set'],['blender','Blender / Food Processor'],
                                 ['kettle','Kettle / Coffee Maker'],['plates','Plates / Crockery Set'],
                                 ['cutlery','Cutlery Set'],['storage','Food Storage / Containers'],
                                 ['gas_stove','Gas Stove / Cooker'],['other','Other']]},
                    {'name': 'material', 'label': 'Material', 'type': 'select', 'required': False,
                     'options': [['stainless','Stainless Steel'],['non_stick','Non-stick / Coated'],
                                 ['cast_iron','Cast Iron'],['glass','Glass'],['ceramic','Ceramic'],
                                 ['plastic','Plastic'],['other','Other']]},
                    {'name': 'quantity', 'label': 'Quantity / Set size', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 5-piece set, 1 item, 12-piece dinner set'},
                ],
            },
            {
                'section_id': 'decor_details',
                'label': 'Décor Details',
                'transaction_types': None,
                'subcategory_types': ['decor'],
                'fields': [
                    {'name': 'decor_type', 'label': 'Type', 'type': 'select', 'required': False,
                     'options': [['curtains','Curtains / Blinds'],['rug','Rug / Carpet'],
                                 ['lamp','Lamp / Lighting'],['wall_art','Wall Art / Picture Frame'],
                                 ['vase','Vase / Ornament'],['clock','Clock'],
                                 ['cushions','Cushions / Pillows'],['mirror','Mirror'],['other','Other']]},
                    {'name': 'colour', 'label': 'Colour', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Beige, Multicolour, White'},
                    {'name': 'dimensions', 'label': 'Dimensions', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 150 × 200 cm (rug), 45 cm height (lamp)'},
                ],
            },
            {
                'section_id': 'condition',
                'label': 'Condition',
                'transaction_types': None,
                'fields': [
                    {'name': 'wear_level', 'label': 'Wear Level', 'type': 'select', 'required': False,
                     'options': [['new','New / unused'],['like_new','Like new — barely used'],
                                 ['good','Good — minor scuffs'],['fair','Fair — noticeable wear'],
                                 ['poor','Poor — significant wear or damage']]},
                    {'name': 'assembly_required', 'label': 'Assembly required', 'type': 'checkbox', 'required': False},
                    {'name': 'delivery_possible', 'label': 'Can arrange delivery', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Logistics',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'quantity_available', 'label': 'Units available', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 20 chairs, 5 tables'},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'delivery_setup', 'label': 'Delivery & setup included', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                ],
            },
        ],
    },

    # ── Health & Beauty ─────────────────────────────────────────────────────
    'health_beauty': {
        'form_sections': [
            {
                'section_id': 'beauty_details',
                'label': 'Beauty & Skincare Details',
                'transaction_types': None,
                'subcategory_types': ['beauty_skincare'],
                'fields': [
                    {'name': 'beauty_item_type', 'label': 'Item Type', 'type': 'select', 'required': True,
                     'options': [['skincare','Skincare / Moisturiser'],['makeup','Makeup / Cosmetics'],
                                 ['fragrance','Fragrance / Perfume'],['haircare','Haircare Product'],
                                 ['hair_extensions','Hair Extensions / Weave'],['wigs','Wigs / Lace Front'],
                                 ['nail_care','Nail Care'],['body_care','Body Care / Lotion'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Neutrogena, Dove, CeraVe, ORS'},
                    {'name': 'skin_type', 'label': 'Suitable Skin Type', 'type': 'select', 'required': False,
                     'options': [['all','All skin types'],['oily','Oily'],['dry','Dry'],
                                 ['combination','Combination'],['sensitive','Sensitive'],['na','Not applicable']]},
                    {'name': 'hair_type', 'label': 'Hair Type', 'type': 'select', 'required': False,
                     'options': [['straight','Straight'],['wavy','Wavy'],['curly','Curly / Coily'],
                                 ['na','Not applicable']]},
                    {'name': 'hair_origin', 'label': 'Hair Origin', 'type': 'select', 'required': False,
                     'options': [['human','Human Hair'],['synthetic','Synthetic'],['na','Not applicable']]},
                    {'name': 'hair_length_inches', 'label': 'Hair Length (inches)', 'type': 'number', 'required': False,
                     'min': 4, 'max': 36, 'placeholder': 'e.g. 18 — hair products only'},
                ],
            },
            {
                'section_id': 'health_details',
                'label': 'Health & Medical Details',
                'transaction_types': None,
                'subcategory_types': ['health'],
                'fields': [
                    {'name': 'health_item_type', 'label': 'Item Type', 'type': 'select', 'required': True,
                     'options': [['supplements','Supplements / Vitamins'],['medical_device','Medical Device / Monitor'],
                                 ['dental','Dental Care'],['first_aid','First Aid'],
                                 ['grooming','Grooming Device (trimmer, shaver)'],
                                 ['massage','Massage / Therapy device'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Omron, Philips, Braun'},
                    {'name': 'power_source', 'label': 'Power Source', 'type': 'select', 'required': False,
                     'options': [['electric','Electric / Mains'],['battery','Battery / AA/AAA'],
                                 ['usb','USB Rechargeable'],['manual','Manual'],['na','Not applicable']]},
                    {'name': 'warranty', 'label': 'Warranty included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'fitness_details',
                'label': 'Fitness Equipment Details',
                'transaction_types': None,
                'subcategory_types': ['fitness'],
                'fields': [
                    {'name': 'fitness_item_type', 'label': 'Item Type', 'type': 'select', 'required': True,
                     'options': [['treadmill','Treadmill'],['exercise_bike','Exercise Bike'],
                                 ['weights','Weights / Dumbbells / Barbell'],['bench','Workout Bench'],
                                 ['multi_gym','Multi-Station Gym'],['resistance','Resistance Bands / Cables'],
                                 ['yoga','Yoga / Pilates Mat & Props'],['rowing','Rowing Machine'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Body Craft, Energym, Marcy'},
                    {'name': 'weight_capacity_kg', 'label': 'Max User Weight (kg)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 120'},
                    {'name': 'power_source', 'label': 'Power Source', 'type': 'select', 'required': False,
                     'options': [['electric','Electric / Motor'],['manual','Manual / Non-motorised'],
                                 ['na','Not applicable']]},
                ],
            },
            {
                'section_id': 'quantity_condition',
                'label': 'Quantity & Condition',
                'transaction_types': None,
                'subcategory_exclude': ['fitness'],
                'fields': [
                    {'name': 'quantity_remaining', 'label': 'Amount remaining', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Unopened, ~80% full, 30 tablets left'},
                    {'name': 'opened', 'label': 'Opened / used', 'type': 'checkbox', 'required': False},
                    {'name': 'expiry_date', 'label': 'Expiry / best before', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 06/2026'},
                    {'name': 'sealed_original', 'label': 'Still sealed in original packaging', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing',
                'transaction_types': ['rental'],
                'subcategory_types': ['fitness', 'health'],
                'fields': [
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'weekly_price', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'cleaning_included', 'label': 'Sanitised between rentals', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                ],
            },
        ],
    },

    # ── Sports & Hobbies ────────────────────────────────────────────────────
    'sports_hobbies': {
        'form_sections': [
            {
                'section_id': 'sports_details',
                'label': 'Sports Equipment Details',
                'transaction_types': None,
                'subcategory_types': ['sports'],
                'fields': [
                    {'name': 'item_type', 'label': 'Item Type', 'type': 'select', 'required': False,
                     'options': [['bicycle','Bicycle / Bike'],['ball','Ball / Sporting ball'],
                                 ['gym_equipment','Gym equipment'],['racket','Racket / Bat / Stick'],
                                 ['water_sports','Water sports gear'],['camping','Camping / Hiking gear'],
                                 ['protective','Protective gear'],['clothing','Sports clothing / footwear'],
                                 ['other','Other']]},
                    {'name': 'sport_activity', 'label': 'Sport / Activity', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Football, Swimming, Cycling, Basketball, Gym'},
                    {'name': 'size', 'label': 'Size / Spec', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Size 5, UK 10, Medium frame'},
                    {'name': 'level', 'label': 'Suitable for', 'type': 'select', 'required': False,
                     'options': [['all','All levels'],['beginner','Beginner / Recreational'],
                                 ['intermediate','Intermediate'],['professional','Professional / Competitive']]},
                    {'name': 'bike_type', 'label': 'Bike Type', 'type': 'select', 'required': False,
                     'options': [['mountain','Mountain Bike (MTB)'],['road','Road / Racing Bike'],
                                 ['city','City / Commuter Bike'],['bmx','BMX'],['kids','Kids Bike'],
                                 ['na','Not applicable']]},
                    {'name': 'wheel_size', 'label': 'Wheel Size (inches)', 'type': 'number', 'required': False,
                     'min': 12, 'max': 29, 'placeholder': 'e.g. 26 — bicycles only'},
                ],
            },
            {
                'section_id': 'musical_instruments',
                'label': 'Instrument Details',
                'transaction_types': None,
                'subcategory_types': ['musical_instruments'],
                'fields': [
                    {'name': 'instrument_type', 'label': 'Instrument Type', 'type': 'select', 'required': True,
                     'options': [['guitar_acoustic','Acoustic Guitar'],['guitar_electric','Electric Guitar'],
                                 ['guitar_bass','Bass Guitar'],['keyboard','Keyboard / Piano'],
                                 ['drums_acoustic','Acoustic Drum Kit'],['drums_electronic','Electronic Drums'],
                                 ['violin','Violin / String'],['trumpet','Trumpet / Brass'],
                                 ['flute','Flute / Wind'],['talking_drum','Talking Drum / Percussion'],
                                 ['dj_equipment','DJ Equipment / Mixer'],['microphone','Microphone'],
                                 ['amplifier','Amplifier / PA Speaker'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Yamaha, Fender, Gibson, Roland, Casio'},
                    {'name': 'case_included', 'label': 'Case / gig bag included', 'type': 'checkbox', 'required': False},
                    {'name': 'accessories_included', 'label': 'Accessories included (straps, cables, sticks)', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'hobbies_details',
                'label': 'Hobby & Activity Details',
                'transaction_types': None,
                'subcategory_types': ['hobbies_art'],
                'fields': [
                    {'name': 'hobby_type', 'label': 'Hobby Type', 'type': 'select', 'required': False,
                     'options': [['board_games','Board Games / Card Games'],['puzzles','Puzzles'],
                                 ['books','Books / Magazines'],['fishing','Fishing Gear'],
                                 ['collecting','Collectibles / Memorabilia'],['other','Other']]},
                    {'name': 'item_count', 'label': 'Number of items / pieces', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 1, 500-piece puzzle, bundle of 10 books'},
                ],
            },
            {
                'section_id': 'condition',
                'label': 'Condition & Usage',
                'transaction_types': None,
                'fields': [
                    {'name': 'usage_frequency', 'label': 'Usage Frequency', 'type': 'select', 'required': False,
                     'options': [['never','Never used'],['few_times','Used a few times'],
                                 ['regularly','Used regularly'],['heavy_use','Heavy use']]},
                    {'name': 'accessories_included', 'label': 'Accessories / extras included', 'type': 'checkbox', 'required': False},
                    {'name': 'original_box', 'label': 'Original packaging / box', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Terms',
                'transaction_types': ['rental'],
                'subcategory_exclude': ['musical_instruments', 'hobbies_art'],
                'fields': [
                    {'name': 'quantity_available', 'label': 'Units available', 'type': 'number', 'required': False, 'min': 1},
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'weekly_price', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'safety_gear_included', 'label': 'Safety / protective gear included', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                ],
            },
        ],
    },

    # ── Tools & Equipment ───────────────────────────────────────────────────
    'tools_equipment': {
        'form_sections': [
            {
                'section_id': 'tool_details',
                'label': 'Tool Details',
                'transaction_types': None,
                'subcategory_exclude': ['office_equipment', 'industrial'],
                'fields': [
                    {'name': 'tool_type', 'label': 'Tool Category', 'type': 'select', 'required': False,
                     'options': [['power_tools','Power tools (drill, grinder, saw)'],
                                 ['hand_tools','Hand tools (spanners, hammers)'],
                                 ['garden','Garden / Landscaping tools'],
                                 ['construction','Construction equipment (mixer, compactor)'],
                                 ['welding','Welding / cutting equipment'],
                                 ['generator','Generator / Power equipment'],
                                 ['measuring','Measuring / surveying instruments'],
                                 ['cleaning','Cleaning equipment'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. INGCO, Bosch, DeWalt, Makita, Total'},
                    {'name': 'model_name', 'label': 'Model', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. PSB 650, GSB 16 RE, DCD791'},
                    {'name': 'power_source', 'label': 'Power Source', 'type': 'select', 'required': False,
                     'options': [['electric','Electric / Mains'],['battery','Battery / Cordless'],
                                 ['manual','Manual / Hand tool'],['petrol','Petrol / Engine'],['solar','Solar']]},
                    {'name': 'voltage', 'label': 'Voltage', 'type': 'select', 'required': False,
                     'options': [['220v','220 / 240V'],['110v','110V'],['universal','Universal / Dual voltage'],
                                 ['na','Not applicable']]},
                    {'name': 'capacity', 'label': 'Capacity / Output', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 2.5 kVA (generator), 650W (drill), 100L (compressor)'},
                ],
            },
            {
                'section_id': 'office_details',
                'label': 'Office Equipment Details',
                'transaction_types': None,
                'subcategory_types': ['office_equipment'],
                'fields': [
                    {'name': 'office_item_type', 'label': 'Item Type', 'type': 'select', 'required': True,
                     'options': [['printer','Printer / Scanner'],['projector','Projector'],
                                 ['shredder','Shredder'],['laminator','Laminator'],
                                 ['photocopier','Photocopier'],['ups','UPS / Battery Backup'],['other','Other']]},
                    {'name': 'brand', 'label': 'Brand', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. HP, Canon, Epson, Brother'},
                    {'name': 'model_name', 'label': 'Model', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. HP LaserJet Pro M404dn'},
                ],
            },
            {
                'section_id': 'industrial_details',
                'label': 'Industrial Equipment Details',
                'transaction_types': None,
                'subcategory_types': ['industrial'],
                'fields': [
                    {'name': 'industrial_type', 'label': 'Equipment Type', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Milling machine, Compressor, Sewing machine, Forklift'},
                    {'name': 'brand', 'label': 'Brand / Manufacturer', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. INGCO, Atlas Copco, Brother'},
                    {'name': 'capacity', 'label': 'Capacity / Output', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 500 kg/h, 10 bar, 5 tonne lift'},
                    {'name': 'dimensions', 'label': 'Dimensions (L × W × H cm)', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 150 × 80 × 120'},
                ],
            },
            {
                'section_id': 'condition',
                'label': 'Condition & Accessories',
                'transaction_types': None,
                'fields': [
                    {'name': 'usage_hours', 'label': 'Approximate usage hours', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Under 50 hours, ~200 hours, Heavy use'},
                    {'name': 'last_serviced', 'label': 'Last serviced', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. January 2024, Never'},
                    {'name': 'accessories_included', 'label': 'Accessories / bits / blades included', 'type': 'checkbox', 'required': False},
                    {'name': 'manual_included', 'label': 'Manual / documentation included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing & Terms',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'quantity_available', 'label': 'Units available', 'type': 'number', 'required': False, 'min': 1},
                    {'name': 'daily_price', 'label': 'Daily Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'weekly_price', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'security_deposit', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'training_provided', 'label': 'Usage training / guidance provided', 'type': 'checkbox', 'required': False},
                    {'name': 'delivery_available', 'label': 'Delivery / pickup available', 'type': 'checkbox', 'required': False},
                ],
            },
        ],
    },

    # ── Handmade & Crafts ───────────────────────────────────────────────────
    'handmade_crafts': {
        'form_sections': [
            {
                'section_id': 'product_details',
                'label': 'Product Details',
                'transaction_types': None,
                'subcategory_exclude': ['candles_soaps', 'jewellery', 'crochet_knitting'],
                'fields': [
                    {'name': 'craft_type', 'label': 'Craft Type', 'type': 'select', 'required': False,
                     'options': [['homeware','Homeware / Decor'],['art_print','Art print / Illustration'],
                                 ['woodwork','Woodwork / Carving'],['pottery','Pottery / Ceramics'],
                                 ['beadwork','Beadwork / Fabric crafts'],['bags_leather','Bags / Leather goods'],
                                 ['resin','Resin Art'],['other','Other']]},
                    {'name': 'materials', 'label': 'Main Materials', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Mahogany, Resin, Ankara fabric'},
                    {'name': 'dimensions', 'label': 'Size / Dimensions', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 30 × 20 cm, One-size fits all'},
                    {'name': 'quantity_available', 'label': 'Units in stock', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 5'},
                ],
            },
            {
                'section_id': 'candles_soaps_details',
                'label': 'Candle & Soap Details',
                'transaction_types': None,
                'subcategory_types': ['candles_soaps'],
                'fields': [
                    {'name': 'product_subtype', 'label': 'Product Type', 'type': 'select', 'required': True,
                     'options': [['candle','Candle'],['soap','Soap / Body Bar'],['wax_melt','Wax Melt'],
                                 ['diffuser','Reed Diffuser'],['other','Other']]},
                    {'name': 'scent', 'label': 'Scent / Fragrance', 'type': 'select', 'required': False,
                     'options': [['floral','Floral'],['citrus','Citrus'],['woody','Woody / Earthy'],
                                 ['vanilla','Vanilla / Sweet'],['fresh','Fresh / Clean'],
                                 ['unscented','Unscented'],['other','Other']]},
                    {'name': 'wax_type', 'label': 'Wax Type', 'type': 'select', 'required': False,
                     'options': [['soy','Soy Wax'],['beeswax','Beeswax'],['paraffin','Paraffin'],
                                 ['coconut','Coconut Wax'],['na','Not applicable (soap / diffuser)']]},
                    {'name': 'burn_time_hours', 'label': 'Burn time (hours)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 40 — candles only'},
                    {'name': 'items_per_unit', 'label': 'Items per pack', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 1 candle, 3-bar soap set'},
                    {'name': 'quantity_available', 'label': 'Units in stock', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 10'},
                ],
            },
            {
                'section_id': 'jewellery_details',
                'label': 'Jewellery Details',
                'transaction_types': None,
                'subcategory_types': ['jewellery'],
                'fields': [
                    {'name': 'jewellery_type', 'label': 'Jewellery Type', 'type': 'select', 'required': True,
                     'options': [['necklace','Necklace / Pendant'],['bracelet','Bracelet / Anklet'],
                                 ['earrings','Earrings'],['ring','Ring'],['brooch','Brooch / Pin'],
                                 ['set','Jewellery Set'],['other','Other']]},
                    {'name': 'metal_type', 'label': 'Metal / Material', 'type': 'select', 'required': False,
                     'options': [['gold','Gold'],['gold_plated','Gold Plated'],['silver','Silver'],
                                 ['brass','Brass / Bronze'],['stainless','Stainless Steel'],
                                 ['beads','Beads / Acrylic'],['other','Other']]},
                    {'name': 'stone_type', 'label': 'Stone / Embellishment', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Crystal, Turquoise, Pearl, None'},
                    {'name': 'hallmarked', 'label': 'Hallmarked / Certified', 'type': 'checkbox', 'required': False},
                    {'name': 'quantity_available', 'label': 'Units in stock', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 3'},
                ],
            },
            {
                'section_id': 'crochet_details',
                'label': 'Crochet & Knitting Details',
                'transaction_types': None,
                'subcategory_types': ['crochet_knitting'],
                'fields': [
                    {'name': 'crochet_item_type', 'label': 'Item Type', 'type': 'select', 'required': True,
                     'options': [['blanket','Blanket / Throw'],['bag','Bag / Tote'],
                                 ['clothing','Clothing / Top / Cardigan'],['hat','Hat / Beanie'],
                                 ['toy','Amigurumi / Toy'],['home_decor','Home Decor'],['other','Other']]},
                    {'name': 'yarn_type', 'label': 'Yarn / Material', 'type': 'select', 'required': False,
                     'options': [['cotton','Cotton'],['acrylic','Acrylic'],['wool','Wool'],
                                 ['mixed','Mixed / Blend'],['other','Other']]},
                    {'name': 'colour', 'label': 'Colour(s)', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Cream & Sage, Multicolour'},
                    {'name': 'size', 'label': 'Size', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 120 × 150 cm, Adult S/M, One size'},
                    {'name': 'quantity_available', 'label': 'Units in stock', 'type': 'number', 'required': False,
                     'min': 1, 'placeholder': 'e.g. 2'},
                ],
            },
            {
                'section_id': 'customisation',
                'label': 'Customisation',
                'transaction_types': None,
                'fields': [
                    {'name': 'made_to_order', 'label': 'Custom / made-to-order available', 'type': 'checkbox', 'required': False},
                    {'name': 'personalisation_available', 'label': 'Personalisation / name engraving available', 'type': 'checkbox', 'required': False},
                    {'name': 'production_days', 'label': 'Production time (days)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 5 (if made to order)'},
                    {'name': 'packaging', 'label': 'Gift packaging available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental Pricing (Decor & Props)',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'rental_item_type', 'label': 'Item Type for Rental', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Centrepieces, Backdrops, Table runners, Decor props'},
                    {'name': 'quantity_available', 'label': 'Units available', 'type': 'number', 'required': False, 'min': 1},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'setup_included', 'label': 'Setup / styling included', 'type': 'checkbox', 'required': False},
                    {'name': 'delivery_area', 'label': 'Delivery coverage area', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Greater Accra only, Nationwide'},
                ],
            },
        ],
    },

    # ── Art & Creative ──────────────────────────────────────────────────────
    'art_creative': {
        'form_sections': [
            {
                'section_id': 'artwork_details',
                'label': 'Artwork Details',
                'transaction_types': None,
                'fields': [
                    {'name': 'medium', 'label': 'Medium / Type', 'type': 'select', 'required': True,
                     'options': [['oil','Oil paint'],['acrylic','Acrylic'],['watercolour','Watercolour'],
                                 ['pencil','Pencil / Charcoal'],['mixed_media','Mixed media'],
                                 ['photography_print','Photography print'],['digital_print','Digital / Giclee print'],
                                 ['sculpture','Sculpture'],['textile','Textile / Fabric art'],
                                 ['illustration','Illustration / Graphic art'],['other','Other']]},
                    {'name': 'dimensions', 'label': 'Dimensions', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. A3, 60 × 90 cm, 18 × 24 inches'},
                    {'name': 'year_created', 'label': 'Year Created', 'type': 'number', 'required': False,
                     'min': 1900, 'max': 2026, 'placeholder': 'e.g. 2023'},
                    {'name': 'artist_name', 'label': 'Artist Name', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Kofi Mensah — leave blank if you prefer not to say'},
                ],
            },
            {
                'section_id': 'authenticity',
                'label': 'Authenticity & Edition',
                'transaction_types': None,
                'fields': [
                    {'name': 'original_or_print', 'label': 'Original or Print', 'type': 'select', 'required': True,
                     'options': [['original','Original artwork (one-of-a-kind)'],
                                 ['limited_print','Limited edition print (state edition number)'],
                                 ['open_print','Open edition print'],
                                 ['digital_file','Digital file / licence']]},
                    {'name': 'edition_info', 'label': 'Edition Number', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 3 of 50'},
                    {'name': 'signed', 'label': 'Signed by artist', 'type': 'checkbox', 'required': False},
                    {'name': 'certificate_included', 'label': 'Certificate of authenticity included', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'display',
                'label': 'Display & Presentation',
                'transaction_types': None,
                'fields': [
                    {'name': 'framed', 'label': 'Framed / mounted', 'type': 'checkbox', 'required': False},
                    {'name': 'ready_to_hang', 'label': 'Ready to hang', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental / Loan Pricing',
                'transaction_types': ['rental'],
                'fields': [
                    {'name': 'monthly_price', 'label': 'Monthly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'installation_included', 'label': 'Installation / hanging included', 'type': 'checkbox', 'required': False},
                    {'name': 'deposit_ghs', 'label': 'Security Deposit (GHS)', 'type': 'number', 'required': False, 'min': 0},
                ],
            },
        ],
    },

    # ── Food, Plants & Nature ───────────────────────────────────────────────
    'food_plants': {
        'form_sections': [
            {
                'section_id': 'plant_identity',
                'label': 'Plant Details',
                'transaction_types': None,
                'subcategory_types': ['potted_plants', 'dwarf_trees', 'flowers'],
                'fields': [
                    {'name': 'quantity', 'label': 'Quantity', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 1 plant, 3 pots'},
                    {'name': 'pot_size', 'label': 'Pot size', 'type': 'select', 'required': False,
                     'options': [['small','Small (under 15 cm)'],['medium','Medium (15–30 cm)'],
                                 ['large','Large (over 30 cm)'],['unpotted','Unpotted / bare root']]},
                    {'name': 'care_level', 'label': 'Care difficulty', 'type': 'select', 'required': False,
                     'options': [['easy','Easy — thrives with minimal attention'],
                                 ['moderate','Moderate — weekly watering & light'],
                                 ['demanding','Demanding — daily attention needed']]},
                    {'name': 'light_requirement', 'label': 'Light requirement', 'type': 'select', 'required': False,
                     'options': [['low','Low light / shade'],['indirect','Bright indirect light'],
                                 ['direct','Full direct sunlight']]},
                    {'name': 'grow_guide_included', 'label': 'Care guide included', 'type': 'checkbox', 'required': False},
                    {'name': 'delivery_possible', 'label': 'Can arrange delivery', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'flowers_details',
                'label': 'Flower Details',
                'transaction_types': None,
                'subcategory_types': ['flowers'],
                'fields': [
                    {'name': 'fresh_or_dried', 'label': 'Fresh or dried', 'type': 'select', 'required': False,
                     'options': [['fresh','Fresh'],['dried','Dried / preserved'],['artificial','Artificial']]},
                    {'name': 'arrangement_type', 'label': 'Arrangement type', 'type': 'select', 'required': False,
                     'options': [['bouquet','Bouquet'],['wreath','Wreath'],['centrepiece','Centrepiece'],
                                 ['loose','Loose stems'],['potted','Potted flowering plant']]},
                ],
            },
            {
                'section_id': 'food_produce_details',
                'label': 'Food & Produce Details',
                'transaction_types': None,
                'subcategory_types': ['food_produce'],
                'fields': [
                    {'name': 'produce_type', 'label': 'Type of produce', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Tomatoes, Plantain, Honey, Eggs'},
                    {'name': 'quantity', 'label': 'Quantity / weight', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 1 crate, 5 kg, 1 dozen'},
                    {'name': 'minimum_order', 'label': 'Minimum order', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 2 kg minimum'},
                    {'name': 'organic', 'label': 'Organically grown', 'type': 'checkbox', 'required': False},
                    {'name': 'expiry_date', 'label': 'Best before / harvest date', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 20 May 2025'},
                ],
            },
            {
                'section_id': 'seeds_details',
                'label': 'Seeds & Seedlings Details',
                'transaction_types': None,
                'subcategory_types': ['seeds_seedlings'],
                'fields': [
                    {'name': 'seed_type', 'label': 'Seed / seedling type', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. Scotch bonnet pepper, Moringa, Tomato F1'},
                    {'name': 'quantity', 'label': 'Quantity', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. 50 seeds, 10 seedling trays'},
                    {'name': 'planting_season', 'label': 'Best planting season', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. March–May (rainy season)'},
                    {'name': 'germination_rate', 'label': 'Germination rate', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. ~85%'},
                ],
            },
            {
                'section_id': 'rental_pricing',
                'label': 'Rental / Event Staging Pricing',
                'transaction_types': ['rental'],
                'subcategory_types': ['potted_plants', 'dwarf_trees', 'flowers'],
                'fields': [
                    {'name': 'quantity_available', 'label': 'Units available for hire', 'type': 'number',
                     'required': False, 'min': 1},
                    {'name': 'per_event_price', 'label': 'Per-event Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'weekly_price', 'label': 'Weekly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'delivery_setup', 'label': 'Delivery & styling included', 'type': 'checkbox', 'required': False},
                ],
            },
        ],
    },

    # ── Services & Commissions ──────────────────────────────────────────────
    'services': {
        'form_sections': [
            {
                'section_id': 'service_details',
                'label': 'Service Details',
                'transaction_types': None,
                'subcategory_exclude': ['tailoring_alterations', 'repairs_maintenance', 'tutoring_lessons', 'photography_videography'],
                'fields': [
                    {'name': 'service_type', 'label': 'Service Type', 'type': 'select', 'required': False,
                     'options': [['design','Graphic Design / Illustration'],['photography','Photography / Videography'],
                                 ['writing','Writing / Copywriting'],['programming','Programming / Tech'],
                                 ['tutoring','Tutoring / Teaching'],['coaching','Coaching / Consulting'],
                                 ['repair','Repair / Technical service'],['tailoring','Tailoring / Alterations'],
                                 ['catering','Catering / Food prep'],['cleaning','Cleaning / Laundry'],
                                 ['beauty','Hair / Beauty / Makeup'],['music','Music / DJ / Entertainment'],
                                 ['moving','Moving / Logistics'],['other','Other']]},
                    {'name': 'delivery_method', 'label': 'How delivered', 'type': 'select', 'required': True,
                     'options': [['in_person','In-person (I travel to client / client comes to me)'],
                                 ['remote','Remote / Online'],['both','Both options available']]},
                    {'name': 'experience_years', 'label': 'Years of experience', 'type': 'select', 'required': False,
                     'options': [['less_1','Less than 1 year'],['1_3','1–3 years'],['3_5','3–5 years'],
                                 ['5_10','5–10 years'],['over_10','Over 10 years']]},
                    {'name': 'free_consultation', 'label': 'Free consultation available', 'type': 'checkbox', 'required': False},
                    {'name': 'languages', 'label': 'Languages served', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. English, Twi, French'},
                ],
            },
            {
                'section_id': 'tailoring_details',
                'label': 'Tailoring Details',
                'transaction_types': None,
                'subcategory_types': ['tailoring_alterations'],
                'fields': [
                    {'name': 'tailoring_type', 'label': 'Speciality', 'type': 'select', 'required': False,
                     'options': [['custom_sewing','Custom sewing / full outfit'],['alterations','Alterations & repairs'],
                                 ['kente_smocking','Kente / Smocking'],['bridal','Bridal & formal'],
                                 ['corporate','Corporate / uniform'],['kids','Children\'s clothing'],
                                 ['accessories','Bags & accessories'],['other','Other']]},
                    {'name': 'delivery_method', 'label': 'How delivered', 'type': 'select', 'required': False,
                     'options': [['in_person','Client visits my shop'],['pickup','I collect & deliver'],
                                 ['both','Both options']]},
                    {'name': 'experience_years', 'label': 'Years of experience', 'type': 'select', 'required': False,
                     'options': [['less_1','Less than 1 year'],['1_3','1–3 years'],['3_5','3–5 years'],
                                 ['5_10','5–10 years'],['over_10','Over 10 years']]},
                    {'name': 'free_consultation', 'label': 'Free measurement / consultation available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'repairs_details',
                'label': 'Repair Details',
                'transaction_types': None,
                'subcategory_types': ['repairs_maintenance'],
                'fields': [
                    {'name': 'repair_type', 'label': 'What do you repair?', 'type': 'select', 'required': False,
                     'options': [['electronics','Electronics & phones'],['appliances','Home appliances'],
                                 ['vehicles','Vehicles & motorcycles'],['plumbing','Plumbing'],
                                 ['electrical','Electrical / wiring'],['furniture','Furniture & upholstery'],
                                 ['shoes_leather','Shoes & leather goods'],['computers','Computers & laptops'],
                                 ['other','Other']]},
                    {'name': 'delivery_method', 'label': 'How delivered', 'type': 'select', 'required': False,
                     'options': [['workshop','Bring item to my workshop'],['on_site','I come to you'],
                                 ['both','Both options']]},
                    {'name': 'warranty_offered', 'label': 'Repair warranty offered', 'type': 'checkbox', 'required': False},
                    {'name': 'free_consultation', 'label': 'Free diagnosis / quote available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'tutoring_details',
                'label': 'Tutoring Details',
                'transaction_types': None,
                'subcategory_types': ['tutoring_lessons'],
                'fields': [
                    {'name': 'subject_area', 'label': 'Subject / skill area', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. WASSCE Maths, Piano, French, Coding'},
                    {'name': 'level', 'label': 'Level taught', 'type': 'select', 'required': False,
                     'options': [['primary','Primary school'],['jhs','JHS / Middle school'],['shs','SHS / Secondary'],
                                 ['tertiary','University / Tertiary'],['adult','Adult / Professional'],['any','Any level']]},
                    {'name': 'delivery_method', 'label': 'How delivered', 'type': 'select', 'required': False,
                     'options': [['in_person','In-person (home visits or your location)'],
                                 ['online','Online (Zoom / Meet)'],['both','Both options']]},
                    {'name': 'experience_years', 'label': 'Years of experience', 'type': 'select', 'required': False,
                     'options': [['less_1','Less than 1 year'],['1_3','1–3 years'],['3_5','3–5 years'],
                                 ['5_10','5–10 years'],['over_10','Over 10 years']]},
                    {'name': 'free_consultation', 'label': 'Free trial session available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'photography_details',
                'label': 'Photography / Videography Details',
                'transaction_types': None,
                'subcategory_types': ['photography_videography'],
                'fields': [
                    {'name': 'photo_type', 'label': 'Speciality', 'type': 'select', 'required': False,
                     'options': [['events','Events (weddings, parties, funerals)'],['portrait','Portrait / headshots'],
                                 ['product','Product & commercial'],['real_estate','Real estate'],
                                 ['documentary','Documentary / journalism'],['videography','Videography'],
                                 ['drone','Drone / aerial'],['other','Other']]},
                    {'name': 'delivery_method', 'label': 'How delivered', 'type': 'select', 'required': False,
                     'options': [['on_location','On location (I travel to you)'],
                                 ['studio','In my studio'],['both','Both options']]},
                    {'name': 'editing_included', 'label': 'Editing / post-production included', 'type': 'checkbox', 'required': False},
                    {'name': 'turnaround_days', 'label': 'Delivery turnaround (days)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 7'},
                    {'name': 'free_consultation', 'label': 'Free consultation / quote available', 'type': 'checkbox', 'required': False},
                ],
            },
            {
                'section_id': 'scope_timeline',
                'label': 'Scope & Timeline',
                'transaction_types': None,
                'subcategory_exclude': ['tailoring_alterations', 'repairs_maintenance', 'tutoring_lessons', 'photography_videography'],
                'fields': [
                    {'name': 'what_is_included', 'label': 'What is included', 'type': 'textarea', 'required': False,
                     'placeholder': 'e.g. Logo design, 3 concepts, 2 revision rounds, final files in PNG + AI'},
                    {'name': 'turnaround_days', 'label': 'Typical turnaround (days)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 3'},
                    {'name': 'revisions', 'label': 'Revision rounds included', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 2'},
                    {'name': 'portfolio_link', 'label': 'Portfolio / sample work', 'type': 'text', 'required': False,
                     'placeholder': 'e.g. instagram.com/yourpage or behance.net/you'},
                ],
            },
            {
                'section_id': 'pricing',
                'label': 'Pricing',
                'transaction_types': None,
                'fields': [
                    {'name': 'price_unit', 'label': 'Price unit', 'type': 'select', 'required': False,
                     'options': [['per_service','Per service / job'],['per_hour','Per hour'],
                                 ['per_day','Per day'],['per_piece','Per piece / item'],
                                 ['per_sqm','Per square metre'],['negotiable','Negotiable']]},
                    {'name': 'hourly_rate', 'label': 'Hourly Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'daily_rate', 'label': 'Day Rate (GHS)', 'type': 'number', 'required': False, 'min': 0},
                    {'name': 'min_booking_hours', 'label': 'Minimum booking (hours)', 'type': 'number', 'required': False,
                     'min': 0, 'placeholder': 'e.g. 2'},
                    {'name': 'advance_booking_days', 'label': 'Advance notice required (days)', 'type': 'number',
                     'required': False, 'min': 0, 'placeholder': 'e.g. 1'},
                    {'name': 'retainer_available', 'label': 'Monthly retainer / ongoing arrangement available',
                     'type': 'checkbox', 'required': False},
                ],
            },
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


def _sanitize_for_prompt(text: str, max_length: int = 400) -> str:
    """Strip characters that could be used for prompt injection before interpolating user input into AI prompts."""
    sanitized = _re.sub(r'[`\\\[\]{}|<>]', '', str(text))
    sanitized = _re.sub(r'(system|assistant|user)\s*:', '', sanitized, flags=_re.IGNORECASE)
    return sanitized[:max_length]


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
    """Call Price Intel service as the sole price source."""
    url = getattr(settings, 'PRICE_INTEL_URL', '')
    if not url:
        return None, None
    try:
        resp = http_client.get(f"{url}/v1/price", params={"q": title}, timeout=5)
        resp.raise_for_status()
        median = resp.json().get("median_ghs")
        if median and float(median) > 0:
            return Decimal(str(round(float(median), 2))), 'price_intel'
    except Exception:
        pass
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
    category = models.CharField(max_length=50)
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
    updated_at = models.DateTimeField(auto_now=True)

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

        self.market_price = mp
        if mp is not None:
            base_price = mp.price_ghs
            self.system_estimated_value = base_price * multiplier
            self.final_estimated_value = (
                (base_price * multiplier * Decimal('0.75')) +
                (self.user_estimated_value * Decimal('0.25'))
            )
        else:
            self.system_estimated_value = None
            self.final_estimated_value = None
        self.save(update_fields=['market_price', 'system_estimated_value', 'final_estimated_value'])


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


REPORT_REASON_CHOICES = [
    ('spam', 'Spam or duplicate'),
    ('prohibited', 'Prohibited item'),
    ('misleading', 'Misleading or fake'),
    ('offensive', 'Offensive content'),
    ('scam', 'Suspected scam'),
    ('other', 'Other'),
]


class ListingReport(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='reported_listings')
    reason = models.CharField(max_length=20, choices=REPORT_REASON_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['listing', 'reporter']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reporter}: {self.reason} on {self.listing}"


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
        f'- Title: {_sanitize_for_prompt(listing.title, 200)}\n'
        f'- Category: {get_category_label(listing.category)}\n'
        f'- Condition: {listing.get_condition_display()}\n'
        f'- Description: {_sanitize_for_prompt(listing.description)}\n\n'
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
        f'- Title: {_sanitize_for_prompt(listing.title, 200)}\n'
        f'- Description: {_sanitize_for_prompt(listing.description)}\n'
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
        get_category_label(listing.category),
        [{'id': c.pk, 'title': c.title, 'description': c.description,
          'category': get_category_label(c.category)} for c in candidates],
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
        get_category_label(listing.category),
        [{'id': c.pk, 'title': c.title, 'description': c.description[:100],
          'category': get_category_label(c.category)} for c in candidates],
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
