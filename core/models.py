import json as _json
import re as _re
import statistics as _statistics
import urllib.parse
import uuid
from decimal import Decimal

import requests as http_client
from django.conf import settings
from django.db import models


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
    ('new', 'New'),
    ('used', 'Used'),
    ('old', 'Old'),
]

CONDITION_MULTIPLIERS = {
    'new': Decimal('1.0'),
    'used': Decimal('0.7'),
    'old': Decimal('0.5'),
}

STATUS_CHOICES = [
    ('pending_review', 'Pending Review'),
    ('active', 'Active'),
    ('closed', 'Closed'),
    ('traded', 'Traded'),
    ('rejected', 'Rejected'),
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
# Category baselines (fallback when no market price is cached)
# ---------------------------------------------------------------------------

class CategoryBaseline(models.Model):
    category = models.CharField(max_length=50, unique=True)
    min_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_value = models.DecimalField(max_digits=10, decimal_places=2)
    typical_value = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category} (typical: {self.typical_value})"


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
        from django.utils import timezone
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
    whatsapp_number = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name or 'User'} ({self.phone})"

    @property
    def display_whatsapp(self):
        return self.whatsapp_number or self.phone


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

class Listing(models.Model):
    user = models.ForeignKey(
        BarterUser, on_delete=models.CASCADE, related_name='listings'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=50, choices=SUBCATEGORY_FLAT_CHOICES, blank=True)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES)
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
    location = models.CharField(max_length=100, blank=True)
    want_text = models.TextField(help_text="What do you want in exchange?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_review')
    rejection_reason = models.TextField(blank=True)
    image = models.ImageField(upload_to='listings/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

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

        # Validate scraped price against category floor — reject implausible values
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

    @property
    def offer_count(self):
        return self.offers.count()


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
# Wishlist items (what users are looking for)
# ---------------------------------------------------------------------------

class WishlistItem(models.Model):
    user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='wishlist_items')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    max_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} wants {self.title}"


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

NOTIFICATION_TYPE_CHOICES = [
    ('wishlist_match', 'Wishlist Match'),
    ('offer_accepted', 'Offer Accepted'),
    ('offer_rejected', 'Offer Rejected'),
    ('seller_demand', 'Seller Demand'),
    ('trade_opportunity', 'Trade Opportunity'),
]


class Notification(models.Model):
    user = models.ForeignKey(BarterUser, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    message = models.CharField(max_length=300)
    link = models.CharField(max_length=200, blank=True)
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
    candidates: list of dicts — id, title, description, category
    Returns: list of dicts — id, score (0.0-1.0), reason  (empty list on any failure)
    Falls back gracefully: callers treat empty return as "use token match as proxy".
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
        'Score > 0.7 only for genuine product-family matches. '
        'Be strict — "iPhone case" does not match "iPhone 14".\n\n'
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


def validate_and_correct_listing_category(listing):
    """
    Use OpenRouter to verify and auto-correct a listing's category and subcategory.
    Only writes changes if confidence >= 0.85 and category/subcategory differs.
    Returns a human-readable correction string, or None if nothing changed.
    """
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        return None

    category_map = _json.dumps({
        slug: {
            'label': label,
            'subcategories': {s: l for s, l in SUBCATEGORY_CHOICES.get(slug, [])},
        }
        for slug, label in CATEGORY_CHOICES
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

    if not result.get('corrected'):
        return None
    if result.get('confidence', 0) < 0.85:
        return None

    new_cat = result.get('category', '').strip()
    new_sub = result.get('subcategory', '').strip()

    valid_cats = {slug for slug, _ in CATEGORY_CHOICES}
    valid_subs = {slug for subs in SUBCATEGORY_CHOICES.values() for slug, _ in subs}

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
    No AI call — used for real-time demand badge on listing pages and pre-approval seller signal.
    """
    from django.db.models import Q
    tokens = {t for t in normalize_item_key(listing.title).split() if len(t) > 2}
    if not tokens:
        return 0
    wishlist_qs = WishlistItem.objects.filter(is_active=True).exclude(user=listing.user)
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
    Stage 1: fast token pre-filter (category + keyword overlap)
    Stage 2: OpenRouter AI scoring — falls back to token match if unavailable
    Budget tolerance read from SiteSettings.
    Called on admin approval (listing becomes active). Returns notification count.
    """
    from django.db.models import Q

    tokens = {t for t in normalize_item_key(listing.title).split() if len(t) > 2}
    if not tokens:
        return 0

    wishlist_qs = WishlistItem.objects.filter(is_active=True).exclude(user=listing.user)
    if listing.category:
        wishlist_qs = wishlist_qs.filter(Q(category=listing.category) | Q(category=''))

    # Stage 1: token pre-filter, cap at 20 candidates
    candidates = []
    for item in wishlist_qs:
        item_tokens = {t for t in normalize_item_key(item.title).split() if len(t) > 2}
        if tokens & item_tokens:
            candidates.append(item)
            if len(candidates) == 20:
                break

    if not candidates:
        return 0

    # Stage 2: AI scoring (fallback: treat all token-matched candidates as score 0.75)
    scored = _score_matches_with_ai(
        listing.title,
        listing.description,
        listing.get_category_display(),
        [{'id': c.pk, 'title': c.title, 'description': c.description, 'category': c.get_category_display() if c.category else ''} for c in candidates],
    )
    score_map = {r['id']: r.get('score', 0) for r in scored} if scored else {c.pk: 0.75 for c in candidates}

    tolerance = Decimal(str(SiteSettings.get().budget_tolerance_pct)) / 100
    notified = 0

    for item in candidates:
        score = score_map.get(item.pk, 0)
        if score < 0.7:
            continue

        # Budget check: skip if listing exceeds budget beyond admin-configured tolerance
        if item.max_budget and listing.final_estimated_value:
            max_allowed = item.max_budget * (Decimal('1') + tolerance)
            if listing.final_estimated_value > max_allowed:
                continue

        # Dedup: never create two wishlist_match notifications for the same (listing, wishlist_item)
        if Notification.objects.filter(
            source_listing=listing,
            source_wishlist_item=item,
            type='wishlist_match',
        ).exists():
            continue

        budget_note = ''
        if item.max_budget and listing.final_estimated_value and listing.final_estimated_value > item.max_budget:
            budget_note = ' (slightly above your budget)'

        Notification.objects.create(
            user=item.user,
            type='wishlist_match',
            message=f'New listing matches your wishlist "{item.title}": {listing.title}{budget_note}',
            link=f'/listings/{listing.pk}/',
            source_listing=listing,
            source_wishlist_item=item,
        )
        notified += 1

    return notified


def match_want_text_to_listings(listing):
    """
    Two-sided matching: find active listings that match what this listing's seller wants,
    and notify those listing owners of a potential trade opportunity.
    Called on admin approval (listing becomes active).
    """
    if not listing.want_text:
        return

    want_tokens = {t for t in normalize_item_key(listing.want_text).split() if len(t) > 2}
    # Strip noise words so "GHS 1500 cash or laptop" still finds laptops
    cash_noise = {'cash', 'money', 'ghs', 'cedis', 'cedi', 'and', 'for', 'the', 'any', 'or'}
    want_tokens -= cash_noise
    if not want_tokens:
        return

    active_listings = (
        Listing.objects.filter(status='active')
        .exclude(user=listing.user)
        .select_related('user')
    )

    # Stage 1: token pre-filter, cap at 20
    candidates = []
    for active in active_listings:
        active_tokens = {t for t in normalize_item_key(active.title).split() if len(t) > 2}
        if want_tokens & active_tokens:
            candidates.append(active)
            if len(candidates) == 20:
                break

    if not candidates:
        return

    # Stage 2: AI scoring
    scored = _score_matches_with_ai(
        listing.want_text,
        f'Seller listed "{listing.title}" and wants: {listing.want_text}',
        listing.get_category_display(),
        [{'id': c.pk, 'title': c.title, 'description': c.description[:100], 'category': c.get_category_display()} for c in candidates],
    )
    score_map = {r['id']: r.get('score', 0) for r in scored} if scored else {c.pk: 0.75 for c in candidates}

    for active in candidates:
        if score_map.get(active.pk, 0) < 0.7:
            continue

        # Dedup: one trade_opportunity notification per (source listing, notified user)
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
    offered_item_description = models.TextField(
        blank=True, help_text="Describe what you are offering in return"
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
    status = models.CharField(
        max_length=20, choices=OFFER_STATUS_CHOICES, default='pending'
    )
    contact_revealed = models.BooleanField(default=False)
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
        if self.message:
            lines.append(f"Message: {self.message}")
        lines.append("Are you interested?")
        text = "\n".join(lines)
        return f"https://wa.me/{number}?text={urllib.parse.quote(text)}"


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
