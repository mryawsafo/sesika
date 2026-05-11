from .models import BarterUser, Offer, Notification


def current_user(request):
    user_id = request.session.get('barter_user_id')
    barter_user = None
    pending_offers_count = 0
    unread_notifications_count = 0
    if user_id:
        try:
            barter_user = BarterUser.objects.get(pk=user_id)
            pending_offers_count = Offer.objects.filter(
                to_user=barter_user, status='pending'
            ).count()
            unread_notifications_count = Notification.objects.filter(
                user=barter_user, is_read=False
            ).count()
        except BarterUser.DoesNotExist:
            pass
    return {
        'barter_user': barter_user,
        'pending_offers_count': pending_offers_count,
        'unread_notifications_count': unread_notifications_count,
    }
