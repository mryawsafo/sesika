from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import WishlistItem, Notification


class Command(BaseCommand):
    help = 'Expire wishlist items that have passed their expiry date'

    def handle(self, *args, **options):
        now = timezone.now()
        expired = WishlistItem.objects.filter(is_active=True, expires_at__lt=now)
        count = expired.count()

        for item in expired:
            item.is_active = False
            item.save(update_fields=['is_active'])
            Notification.objects.create(
                user=item.user,
                type='wishlist_expiring',
                message=(
                    f'Your wishlist item "{item.title}" has expired. '
                    'Renew it to keep receiving match notifications.'
                ),
                link='/my/wishlist/',
            )

        self.stdout.write(self.style.SUCCESS(f'Expired {count} wishlist item(s).'))
