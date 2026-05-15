from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from .models import (
    BarterUser, Listing, ListingPhoto, Offer, CategoryBaseline, MarketPrice, PriceSample,
    SavedListing, WishlistItem, Notification, SiteSettings, UniversityDomain,
    CampusGroup, CampusMembership, TradeRating,
    match_listing_to_wishlists, match_want_text_to_listings,
    validate_and_correct_listing_category, enrich_listing_with_ai,
    DeviceToken, LoginAttempt, Category, Subcategory, invalidate_category_cache,
)


@admin.register(BarterUser)
class BarterUserAdmin(admin.ModelAdmin):
    list_display = ('phone', 'name', 'is_verified', 'is_student_verified', 'location_display_col', 'completed_trades', 'created_at')
    list_filter = ('is_verified', 'is_student_verified', 'location_region', 'contact_reveal_preference')
    search_fields = ('phone', 'name', 'student_email')

    @admin.display(description='Location')
    def location_display_col(self, obj):
        return obj.location_display or '—'

    @admin.display(description='Trades')
    def completed_trades(self, obj):
        return obj.completed_trades_count

    @admin.display(description='Devices')
    def device_count(self, obj):
        return obj.device_tokens.count()


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0
    readonly_fields = ('photo_preview',)
    fields = ('photo_preview', 'image', 'order')

    @admin.display(description='Preview')
    def photo_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:60px; border-radius:4px;" />', obj.image.url)
        return '—'


@admin.register(CategoryBaseline)
class CategoryBaselineAdmin(admin.ModelAdmin):
    list_display = ('category', 'min_value', 'typical_value', 'max_value')


class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1
    fields = ('slug', 'label', 'display_order', 'is_active')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('label', 'slug', 'icon', 'display_order', 'is_active', 'subcategory_count')
    list_filter = ('is_active',)
    search_fields = ('slug', 'label')
    inlines = [SubcategoryInline]
    prepopulated_fields = {'slug': ('label',)}

    @admin.display(description='Subcategories')
    def subcategory_count(self, obj):
        return obj.subcategories.filter(is_active=True).count()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        invalidate_category_cache()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        invalidate_category_cache()


@admin.register(PriceSample)
class PriceSampleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price_ghs', 'scraped_at')
    list_filter = ('category',)
    search_fields = ('title',)
    readonly_fields = ('title', 'price_ghs', 'category', 'scraped_at')

    def has_add_permission(self, request):
        return False


@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ('item_key', 'category', 'subcategory', 'price_ghs', 'source', 'sample_count', 'last_updated')
    list_filter = ('category', 'source')
    search_fields = ('item_key',)
    readonly_fields = ('item_key', 'created_at', 'last_updated')


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'category', 'condition', 'transaction_type',
        'listing_type', 'market_price_display', 'final_estimated_value',
        'status', 'ai_status', 'suggestion_flag', 'created_at',
    )
    list_filter = ('category', 'condition', 'status', 'transaction_type', 'listing_type', 'listing_behaviour')
    search_fields = ('title', 'description')
    inlines = [ListingPhotoInline]
    readonly_fields = ('ai_enrichment_display',)

    fieldsets = [
        ('Core', {
            'fields': [
                'user', 'title', 'category', 'subcategory', 'description',
                'condition', 'listing_type', 'transaction_type',
            ],
        }),
        ('Duration & Location', {
            'fields': [
                'listing_behaviour', 'duration_days', 'expires_at',
                'location_region', 'location_city', 'location_neighbourhood',
                'collection_method',
            ],
        }),
        ('Trade Details', {
            'fields': ['want_text', 'cash_topup_direction', 'user_estimated_value',
                       'system_estimated_value', 'final_estimated_value', 'market_price'],
        }),
        ('Category-specific', {
            'classes': ['collapse'],
            'fields': [
                'brand', 'model_name', 'size', 'colour', 'gender',
                'materials_used', 'service_scope', 'service_timeline_days',
                'repair_description', 'warranty_offered', 'warranty_duration_days',
            ],
        }),
        ('Rental', {
            'classes': ['collapse'],
            'fields': [
                'rental_period_unit', 'rental_payment_description',
                'deposit_required', 'deposit_description',
                'availability_notes', 'rental_conditions',
            ],
        }),
        ('Structured Attributes', {
            'classes': ['collapse'],
            'fields': ['attributes'],
        }),
        ('AI Enrichment', {
            'fields': [
                'ai_enrichment_display', 'ai_enrichment',
                'ai_enrichment_hidden', 'ai_enrichment_flagged', 'ai_enrichment_admin_edited',
            ],
        }),
        ('SEO', {
            'classes': ['collapse'],
            'fields': ['slug', 'seo_title', 'seo_description'],
        }),
        ('Suggested Category', {
            'description': 'User-submitted category suggestion. Use the "Create suggested category and approve" action to add it to the DB and activate the listing.',
            'fields': ['suggested_category', 'suggested_subcategory'],
        }),
        ('Status', {
            'fields': ['status', 'rejection_reason'],
        }),
    ]

    @admin.display(description='Market Price')
    def market_price_display(self, obj):
        if obj.market_price:
            return f"GHS {obj.market_price.price_ghs:,.0f} ({obj.market_price.source})"
        return "—"

    @admin.display(description='AI')
    def ai_status(self, obj):
        if obj.ai_enrichment_flagged:
            return format_html('<span style="color:red;">⚑ Flagged</span>')
        if obj.ai_enrichment_admin_edited:
            return format_html('<span style="color:green;">✎ Edited</span>')
        if obj.ai_enrichment_hidden:
            return format_html('<span style="color:gray;">— Hidden</span>')
        if obj.ai_enrichment:
            return '✓'
        return '—'

    @admin.display(description='New Cat?')
    def suggestion_flag(self, obj):
        if obj.suggested_category:
            return format_html('<span style="background:#fef3c7; color:#92400e; border-radius:4px; padding:2px 6px; font-size:0.75rem; font-weight:600;">⚡ {}</span>', obj.suggested_category)
        return '—'

    @admin.display(description='AI enrichment (current)')
    def ai_enrichment_display(self, obj):
        if not obj.ai_enrichment:
            return 'No AI enrichment yet.'
        import json
        pretty = json.dumps(obj.ai_enrichment, indent=2)
        return format_html('<pre style="font-size:0.8em; max-height:200px; overflow:auto;">{}</pre>', pretty)

    actions = ['approve_listings', 'reject_listings', 'fetch_images', 'clear_ai_flag']

    @admin.action(description='✅ Approve selected listings')
    def approve_listings(self, request, queryset):
        to_approve = list(queryset.filter(status__in=['pending_review', 'rejected']))
        queryset.filter(status__in=['pending_review', 'rejected']).update(status='active', rejection_reason='')

        corrections = []
        enriched = 0
        new_cats = []
        for listing in to_approve:
            listing.refresh_from_db()

            if listing.category == 'other' and listing.suggested_category:
                cat_slug = slugify(listing.suggested_category)[:50]
                cat, _ = Category.objects.get_or_create(
                    slug=cat_slug,
                    defaults={'label': listing.suggested_category, 'display_order': 99},
                )
                listing.category = cat_slug
                if listing.suggested_subcategory:
                    sub_slug = slugify(listing.suggested_subcategory)[:50]
                    Subcategory.objects.get_or_create(
                        category=cat, slug=sub_slug,
                        defaults={'label': listing.suggested_subcategory, 'display_order': 99},
                    )
                    listing.subcategory = sub_slug
                listing.suggested_category = ''
                listing.suggested_subcategory = ''
                listing.save(update_fields=['category', 'subcategory', 'suggested_category', 'suggested_subcategory'])
                new_cats.append(cat.label)

            correction = validate_and_correct_listing_category(listing)
            if correction:
                corrections.append(correction)
            match_listing_to_wishlists(listing)
            match_want_text_to_listings(listing)
            enrich_listing_with_ai(listing)
            enriched += 1

        msg = f'{len(to_approve)} listing(s) approved, {enriched} enriched.'
        if new_cats:
            msg += f' New categories added to platform: {", ".join(new_cats)}.'
        if corrections:
            msg += f' Auto-corrected {len(corrections)}: ' + '; '.join(corrections)
        self.message_user(request, msg)

    @admin.action(description='❌ Reject selected listings')
    def reject_listings(self, request, queryset):
        reason = request.POST.get('rejection_reason', 'Does not meet listing guidelines.')
        updated = queryset.exclude(status='traded').update(status='rejected', rejection_reason=reason)
        self.message_user(request, f'{updated} listing(s) rejected.')

    @admin.action(description='🔍 Fetch images for selected listings (no image only)')
    def fetch_images(self, request, queryset):
        from django.core.management import call_command
        ids = list(queryset.filter(photos__isnull=True).values_list('pk', flat=True))
        if not ids:
            self.message_user(request, 'All selected listings already have images.')
            return
        call_command('fetch_listing_images', listing_ids=ids)
        self.message_user(request, f'Image fetch triggered for {len(ids)} listing(s).')

    @admin.action(description='✓ Clear AI flag on selected listings')
    def clear_ai_flag(self, request, queryset):
        updated = queryset.update(ai_enrichment_flagged=False, ai_enrichment_admin_edited=True)
        self.message_user(request, f'{updated} listing(s) AI flag cleared.')

    def save_model(self, request, obj, form, change):
        if change and 'ai_enrichment' in form.changed_data:
            obj.ai_enrichment_admin_edited = True
            obj.ai_enrichment_flagged = False
            obj.ai_enrichment_hidden = False
        super().save_model(request, obj, form, change)
        if change and 'ai_enrichment' in form.changed_data:
            from .models import Notification
            Notification.objects.create(
                user=obj.user,
                type='ai_section_updated',
                message=f'An admin has reviewed and updated the AI-generated section on your listing "{obj.title}".',
                link=f'/listings/{obj.pk}/',
                source_listing=obj,
            )


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'want_type', 'term_type', 'condition_acceptable', 'max_budget', 'is_active', 'expires_at', 'created_at')
    list_filter = ('category', 'is_active', 'want_type', 'term_type')
    search_fields = ('title', 'user__name', 'user__phone')


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('listing', 'from_user', 'offer_type', 'cash_topup', 'counter_cash_topup', 'contact_revealed', 'status', 'pending_timeout_notified_at', 'created_at')
    list_filter = ('status', 'contact_revealed', 'offer_type')
    search_fields = ('listing__title', 'from_user__name', 'from_user__phone')


@admin.register(TradeRating)
class TradeRatingAdmin(admin.ModelAdmin):
    list_display = ('rater', 'rated_user', 'score', 'offer', 'created_at')
    list_filter = ('score',)
    search_fields = ('rater__name', 'rated_user__name')


@admin.register(UniversityDomain)
class UniversityDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'university_name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('domain', 'university_name')


@admin.register(CampusGroup)
class CampusGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'university_name', 'domain', 'is_active', 'member_count', 'created_at')
    list_filter = ('is_active',)

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj.members.count()


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'short_token', 'ip_address', 'short_ua', 'created_at', 'last_seen')
    list_filter = ('created_at',)
    search_fields = ('user__phone', 'ip_address')
    readonly_fields = ('token', 'user', 'user_agent', 'ip_address', 'created_at', 'last_seen')

    @admin.display(description='Token')
    def short_token(self, obj):
        return str(obj.token)[:8] + '…'

    @admin.display(description='Browser / Device')
    def short_ua(self, obj):
        return obj.user_agent[:60] + ('…' if len(obj.user_agent) > 60 else '')


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('phone', 'success', 'ip_address', 'short_ua', 'timestamp')
    list_filter = ('success',)
    search_fields = ('phone', 'ip_address')
    readonly_fields = ('phone', 'ip_address', 'user_agent', 'success', 'timestamp')
    date_hierarchy = 'timestamp'

    @admin.display(description='Browser / Device')
    def short_ua(self, obj):
        return obj.user_agent[:60] + ('…' if len(obj.user_agent) > 60 else '')


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Wishlist Matching', {
            'fields': ['budget_tolerance_pct', 'wishlist_default_expiry_days'],
            'description': 'Controls wishlist matching and expiry behaviour.',
        }),
        ('Offer Management', {
            'fields': ['offer_timeout_days'],
            'description': 'Days before a pending offer is flagged to admin for manual follow-up.',
        }),
        ('Listing Freshness', {
            'fields': ['listing_stale_days'],
            'description': 'Days before an active permanent listing with no matches prompts a review.',
        }),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'match_tier', 'message', 'is_read', 'clicked_at', 'created_at')
    list_filter = ('type', 'is_read', 'match_tier')
    search_fields = ('user__phone', 'message')
    readonly_fields = ('clicked_at', 'source_listing', 'source_wishlist_item')
