from django.contrib import admin
from django.utils.html import format_html
from .models import (
    BarterUser, Listing, Offer, CategoryBaseline, MarketPrice, PriceSample,
    SavedListing, WishlistItem, Notification, SiteSettings,
    match_listing_to_wishlists, match_want_text_to_listings,
    validate_and_correct_listing_category, DeviceToken, LoginAttempt,
)


@admin.register(BarterUser)
class BarterUserAdmin(admin.ModelAdmin):
    list_display = ('phone', 'name', 'is_verified', 'device_count', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('phone', 'name')

    @admin.display(description='Devices')
    def device_count(self, obj):
        return obj.device_tokens.count()


@admin.register(CategoryBaseline)
class CategoryBaselineAdmin(admin.ModelAdmin):
    list_display = ('category', 'min_value', 'typical_value', 'max_value')


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
    list_display = ('title', 'user', 'category', 'subcategory', 'condition', 'market_price_display', 'final_estimated_value', 'status', 'created_at')
    list_filter = ('category', 'subcategory', 'condition', 'status')
    search_fields = ('title', 'description')

    @admin.display(description='Market Price Used')
    def market_price_display(self, obj):
        if obj.market_price:
            return f"GHS {obj.market_price.price_ghs:,.0f} ({obj.market_price.source})"
        return "—"
    actions = ['approve_listings', 'reject_listings', 'fetch_images']

    @admin.action(description='✅ Approve selected listings')
    def approve_listings(self, request, queryset):
        to_approve = list(queryset.filter(status__in=['pending_review', 'rejected']))
        queryset.filter(status__in=['pending_review', 'rejected']).update(status='active', rejection_reason='')

        corrections = []
        for listing in to_approve:
            listing.status = 'active'
            correction = validate_and_correct_listing_category(listing)
            if correction:
                corrections.append(correction)
            match_listing_to_wishlists(listing)
            match_want_text_to_listings(listing)

        msg = f'{len(to_approve)} listing(s) approved.'
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
        ids = list(queryset.filter(image='').values_list('pk', flat=True))
        if not ids:
            self.message_user(request, 'All selected listings already have images.')
            return
        call_command('fetch_listing_images', listing_ids=ids)
        self.message_user(request, f'Image fetch triggered for {len(ids)} listing(s).')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'max_budget', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'user__name', 'user__phone')


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('listing', 'from_user', 'cash_topup', 'contact_revealed', 'status', 'created_at')
    list_filter = ('status', 'contact_revealed')


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
            'fields': ['budget_tolerance_pct'],
            'description': (
                'Controls the AI-powered wishlist matching engine. '
                'Changes take effect immediately on the next listing approval.'
            ),
        }),
    ]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'message', 'is_read', 'clicked_at', 'created_at')
    list_filter = ('type', 'is_read')
    search_fields = ('user__phone', 'message')
    readonly_fields = ('clicked_at', 'source_listing', 'source_wishlist_item')
