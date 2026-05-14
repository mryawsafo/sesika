from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Offer, Notification, SiteSettings


class Command(BaseCommand):
    help = 'Notify admin of offers that have been pending beyond the timeout window'

    def handle(self, *args, **options):
        settings = SiteSettings.get()
        timeout_days = settings.offer_timeout_days
        cutoff = timezone.now() - timedelta(days=timeout_days)

        stale = Offer.objects.filter(
            status='pending',
            created_at__lt=cutoff,
            pending_timeout_notified_at__isnull=True,
        ).select_related('from_user', 'to_user', 'listing')

        count = stale.count()
        for offer in stale:
            Notification.objects.create(
                user=offer.to_user,
                type='offer_timeout',
                message=(
                    f'You have an offer on "{offer.listing.title}" from '
                    f'{offer.from_user.name or offer.from_user.phone} that '
                    f'has been pending for {timeout_days}+ days. Please respond.'
                ),
                link='/my/offers/',
                source_listing=offer.listing,
            )
            offer.pending_timeout_notified_at = timezone.now()
            offer.save(update_fields=['pending_timeout_notified_at'])

        self.stdout.write(self.style.SUCCESS(f'Flagged {count} timed-out offer(s).'))
