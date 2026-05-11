import json
import logging
import uuid
from decimal import Decimal
from django.db.models import Count

logger = logging.getLogger(__name__)

import requests as http_client
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import (
    BarterUser, Listing, Offer, CategoryBaseline, CONDITION_MULTIPLIERS,
    CATEGORY_CHOICES, SUBCATEGORY_CHOICES, SavedListing, WishlistItem,
    Notification, match_listing_to_wishlists, match_want_text_to_listings,
    count_wishlist_demand, DeviceToken, LoginAttempt,
)
from .forms import LoginForm, ListingForm, OfferForm, WishlistItemForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_current_user(request):
    """Return BarterUser from session, or None."""
    user_id = request.session.get('barter_user_id')
    if user_id:
        try:
            return BarterUser.objects.get(pk=user_id)
        except BarterUser.DoesNotExist:
            pass
    return None


def post_login_redirect(user):
    """Return the redirect target after a successful login."""
    if not user.name:
        return 'complete_profile'
    return 'home'


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def login_required_barter(view_fn):
    """Decorator: redirect to login if no session user."""
    def wrapper(request, *args, **kwargs):
        if not get_current_user(request):
            messages.warning(request, 'Please log in first.')
            return redirect('login')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


def verified_required(view_fn):
    """Decorator: redirect to OTP page if this device is not verified."""
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            messages.warning(request, 'Please log in first.')
            return redirect('login')
        if not request.session.get('device_verified'):
            messages.warning(request, 'You must verify your phone number first.')
            return redirect('request_otp')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def login_view(request):
    if get_current_user(request):
        return redirect('home')

    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        if form.is_valid():
            phone = form.cleaned_data['phone']
            user, _ = BarterUser.objects.get_or_create(phone=phone)
            request.session['barter_user_id'] = user.pk
            LoginAttempt.objects.create(phone=phone, ip_address=ip, user_agent=ua, success=True)

            # Already verified — trust them and set session flag
            if user.is_verified:
                request.session['device_verified'] = True
                messages.success(request, f'Welcome back, {user.name or user.phone}!')
                return redirect(post_login_redirect(user))

            messages.info(request, 'Please verify your number to continue.')
            return redirect('request_otp')
        else:
            raw_phone = request.POST.get('phone', '')
            LoginAttempt.objects.create(phone=raw_phone, ip_address=ip, user_agent=ua, success=False)

    return render(request, 'core/login.html', {'form': form})


@login_required_barter
def logout_view(request):
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('login')


@login_required_barter
def request_otp(request):
    user = get_current_user(request)

    whatsapp_url = request.session.get('otp_whatsapp_url')
    token = request.session.get('otp_token')
    error = None
    pending_message = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate':
            try:
                resp = http_client.post(
                    f"{settings.FREE_OTP_SERVICE_URL}/v1/verifications/",
                    json={"phone_number": user.phone},
                    timeout=10,
                )
                resp.raise_for_status()
                data = resp.json()
                request.session['otp_verification_id'] = str(data['id'])
                request.session['otp_whatsapp_url'] = data['whatsapp_url']
                request.session['otp_token'] = data['token']
                whatsapp_url = data['whatsapp_url']
                token = data['token']
            except Exception as e:
                logger.error("OTP generate failed — URL: %s | Error: %s", settings.FREE_OTP_SERVICE_URL, e)
                error = 'Could not reach verification service. Please try again.'

        elif action == 'check':
            verification_id = request.session.get('otp_verification_id')
            if not verification_id:
                error = 'No active verification. Please generate a new one.'
            else:
                status_data = None
                try:
                    resp = http_client.get(
                        f"{settings.FREE_OTP_SERVICE_URL}/v1/verifications/{verification_id}",
                        timeout=10,
                    )
                    resp.raise_for_status()
                    status_data = resp.json()
                except Exception as e:
                    logger.error("OTP check failed — URL: %s | Error: %s", settings.FREE_OTP_SERVICE_URL, e)
                    error = 'Could not reach verification service. Please try again.'

                if status_data:
                    if status_data['status'] == 'verified':
                        user.is_verified = True
                        user.save()
                        for key in ('otp_verification_id', 'otp_whatsapp_url', 'otp_token'):
                            request.session.pop(key, None)
                        request.session['device_verified'] = True

                        token_value = uuid.uuid4()
                        DeviceToken.objects.create(
                            user=user,
                            token=token_value,
                            user_agent=request.META.get('HTTP_USER_AGENT', ''),
                            ip_address=get_client_ip(request),
                        )

                        messages.success(request, '✅ Phone verified! You can now list items and make offers.')
                        response = redirect(post_login_redirect(user))
                        response.set_cookie(
                            'barter_device_token',
                            str(token_value),
                            max_age=30 * 24 * 60 * 60,
                            httponly=True,
                            samesite='Lax',
                        )
                        return response
                    elif status_data['status'] in ('expired', 'failed'):
                        for key in ('otp_verification_id', 'otp_whatsapp_url', 'otp_token'):
                            request.session.pop(key, None)
                        whatsapp_url = None
                        token = None
                        error = 'Verification expired or failed. Please generate a new one.'
                    else:
                        pending_message = "Still waiting — make sure you sent the WhatsApp message, then try again."

    return render(request, 'core/request_otp.html', {
        'user': user,
        'whatsapp_url': whatsapp_url,
        'token': token,
        'error': error,
        'pending_message': pending_message,
    })


@login_required_barter
def verify_otp(request):
    return redirect('request_otp')


@login_required_barter
def complete_profile(request):
    user = get_current_user(request)
    if user.name:
        return redirect('home')

    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        if not name:
            error = 'Please enter your name.'
        else:
            user.name = name
            if location:
                user.location = location
            user.save()
            return redirect('home')

    return render(request, 'core/complete_profile.html', {'user': user, 'error': error})


@login_required_barter
def update_profile(request):
    user = get_current_user(request)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        location = request.POST.get('location', '').strip()
        whatsapp = request.POST.get('whatsapp_number', '').strip()
        if name:
            user.name = name
        if location:
            user.location = location
        if whatsapp:
            user.whatsapp_number = whatsapp
        user.save()
        messages.success(request, 'Profile updated.')
        return redirect('home')
    return render(request, 'core/profile.html', {'barter_user': user})


# ---------------------------------------------------------------------------
# Listing views
# ---------------------------------------------------------------------------

def home(request):
    listings = Listing.objects.filter(status='active').select_related('user')
    category_filter = request.GET.get('category', '')
    if category_filter:
        listings = listings.filter(category=category_filter)

    current_user = get_current_user(request)
    saved_pks = set()
    if current_user:
        saved_pks = set(
            SavedListing.objects.filter(user=current_user)
            .values_list('listing_id', flat=True)
        )

    return render(request, 'core/home.html', {
        'listings': listings,
        'category_choices': CATEGORY_CHOICES,
        'selected_category': category_filter,
        'saved_pks': saved_pks,
    })


def listing_detail(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    current_user = get_current_user(request)

    user_offer = None
    is_saved = False
    if current_user:
        user_offer = Offer.objects.filter(
            listing=listing, from_user=current_user
        ).order_by('-created_at').first()
        is_saved = SavedListing.objects.filter(user=current_user, listing=listing).exists()

    demand_count = count_wishlist_demand(listing)

    return render(request, 'core/listing_detail.html', {
        'listing': listing,
        'user_offer': user_offer,
        'is_owner': current_user and current_user.pk == listing.user.pk,
        'is_saved': is_saved,
        'demand_count': demand_count,
    })


@verified_required
def listing_create(request):
    user = get_current_user(request)
    if not user.name:
        return redirect('complete_profile')
    form = ListingForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        listing = form.save(commit=False)
        listing.user = user
        listing.save()
        listing.compute_and_save_value()

        # Pre-approval: notify seller of potential demand immediately
        demand_count = count_wishlist_demand(listing)
        if demand_count > 0:
            person_word = 'person' if demand_count == 1 else 'people'
            verb = 'is' if demand_count == 1 else 'are'
            Notification.objects.create(
                user=user,
                type='seller_demand',
                message=f'{demand_count} {person_word} on the platform {verb} looking for something like "{listing.title}". Get approved to connect!',
                link=f'/listings/{listing.pk}/',
                source_listing=listing,
            )

        messages.success(request, '✅ Listing submitted for review!')
        return redirect('listing_detail', pk=listing.pk)

    return render(request, 'core/listing_form.html', {
        'form': form,
        'action': 'Create',
        'subcategory_choices_json': json.dumps(SUBCATEGORY_CHOICES),
    })


@verified_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    user = get_current_user(request)

    if listing.user.pk != user.pk:
        messages.error(request, 'You can only edit your own listings.')
        return redirect('listing_detail', pk=pk)

    form = ListingForm(request.POST or None, request.FILES or None, instance=listing)
    if request.method == 'POST' and form.is_valid():
        listing = form.save(commit=False)
        listing.save()
        listing.compute_and_save_value()
        messages.success(request, 'Listing updated.')
        return redirect('listing_detail', pk=listing.pk)

    return render(request, 'core/listing_form.html', {
        'form': form,
        'action': 'Edit',
        'listing': listing,
        'subcategory_choices_json': json.dumps(SUBCATEGORY_CHOICES),
    })


@verified_required
@require_POST
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    user = get_current_user(request)

    if listing.user.pk != user.pk:
        messages.error(request, 'You can only delete your own listings.')
        return redirect('listing_detail', pk=pk)

    listing.delete()
    messages.success(request, 'Listing deleted.')
    return redirect('home')


# ---------------------------------------------------------------------------
# Offer views
# ---------------------------------------------------------------------------

@verified_required
def offer_create(request, listing_pk):
    listing = get_object_or_404(Listing, pk=listing_pk, status='active')
    user = get_current_user(request)

    if listing.user.pk == user.pk:
        messages.error(request, 'You cannot make an offer on your own listing.')
        return redirect('listing_detail', pk=listing_pk)

    # Compute suggestion for display before form submission
    target_value = listing.final_estimated_value or listing.user_estimated_value
    suggested_min = (target_value * Decimal('0.8')).quantize(Decimal('0.01'))
    suggested_max = (target_value * Decimal('1.2')).quantize(Decimal('0.01'))

    form = OfferForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        offered_value = form.cleaned_data.get('offered_item_value') or Decimal('0')
        cash_topup = form.cleaned_data.get('cash_topup') or Decimal('0')

        offer = Offer(
            from_user=user,
            to_user=listing.user,
            listing=listing,
            offered_item_description=form.cleaned_data.get('offered_item_description', ''),
            cash_topup=cash_topup,
            message=form.cleaned_data.get('message', ''),
        )
        offer.compute_suggested_topup(offered_value + cash_topup)
        offer.save()

        messages.success(
            request,
            '🎉 Offer submitted! The seller\'s WhatsApp contact is now unlocked.'
        )
        return redirect('offer_success', offer_pk=offer.pk)

    return render(request, 'core/offer_form.html', {
        'form': form,
        'listing': listing,
        'suggested_min': suggested_min,
        'suggested_max': suggested_max,
        'target_value': target_value,
    })


@login_required_barter
def offer_success(request, offer_pk):
    offer = get_object_or_404(Offer, pk=offer_pk)
    user = get_current_user(request)

    if offer.from_user.pk != user.pk:
        messages.error(request, 'Access denied.')
        return redirect('home')

    # Mark contact as revealed
    if not offer.contact_revealed:
        offer.contact_revealed = True
        offer.save()

    whatsapp_link = offer.whatsapp_link()
    return render(request, 'core/offer_success.html', {
        'offer': offer,
        'whatsapp_link': whatsapp_link,
    })


# ---------------------------------------------------------------------------
# Offer suggest (AJAX / form helper)
# ---------------------------------------------------------------------------

def offer_suggest(request):
    """
    GET ?listing_id=X&offered_value=Y
    Returns JSON with suggested min/max cash top-up.
    """
    listing_id = request.GET.get('listing_id')
    offered_value_raw = request.GET.get('offered_value', '0')

    try:
        listing = Listing.objects.get(pk=listing_id)
    except (Listing.DoesNotExist, TypeError, ValueError):
        return JsonResponse({'error': 'Listing not found'}, status=404)

    try:
        offered_value = Decimal(offered_value_raw)
    except Exception:
        offered_value = Decimal('0')

    target = listing.final_estimated_value or listing.user_estimated_value
    diff = target - offered_value
    if diff < 0:
        diff = Decimal('0')

    return JsonResponse({
        'target_value': str(target),
        'suggested_min': str((diff * Decimal('0.8')).quantize(Decimal('0.01'))),
        'suggested_max': str((diff * Decimal('1.2')).quantize(Decimal('0.01'))),
    })


# ---------------------------------------------------------------------------
# My listings / offers dashboard
# ---------------------------------------------------------------------------

@login_required_barter
def my_listings(request):
    user = get_current_user(request)
    listings = Listing.objects.filter(user=user).order_by('-created_at')
    return render(request, 'core/my_listings.html', {'listings': listings})


@login_required_barter
@require_POST
def offer_update_status(request, offer_pk):
    user = get_current_user(request)
    offer = get_object_or_404(Offer, pk=offer_pk, to_user=user)
    action = request.POST.get('action')

    if offer.status == 'pending':
        if action == 'accept':
            offer.status = 'accepted'
            offer.contact_revealed = True
            offer.save()
            offer.listing.status = 'traded'
            offer.listing.save()
            messages.success(request, f'Offer accepted. {offer.from_user.name or offer.from_user.phone} can now contact you.')
            Notification.objects.create(
                user=offer.from_user,
                type='offer_accepted',
                message=f'Your offer on "{offer.listing.title}" was accepted! Contact the seller.',
                link=f'/offers/{offer.pk}/success/',
            )
        elif action == 'reject':
            offer.status = 'rejected'
            offer.save()
            messages.info(request, 'Offer rejected.')
            Notification.objects.create(
                user=offer.from_user,
                type='offer_rejected',
                message=f'Your offer on "{offer.listing.title}" was not accepted.',
                link=f'/listings/{offer.listing.pk}/',
            )

    return redirect('my_offers')


@login_required_barter
def my_offers(request):
    user = get_current_user(request)
    offers_made = Offer.objects.filter(from_user=user).select_related('listing', 'to_user')
    offers_received = Offer.objects.filter(to_user=user).select_related('listing', 'from_user')
    return render(request, 'core/my_offers.html', {
        'offers_made': offers_made,
        'offers_received': offers_received,
    })


# ---------------------------------------------------------------------------
# Saved listings
# ---------------------------------------------------------------------------

@login_required_barter
@require_POST
def listing_save_toggle(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    user = get_current_user(request)
    saved = SavedListing.objects.filter(user=user, listing=listing).first()
    if saved:
        saved.delete()
        messages.info(request, 'Removed from saved listings.')
    else:
        SavedListing.objects.create(user=user, listing=listing)
        messages.success(request, 'Listing saved.')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('listing_detail', pk=pk)


@login_required_barter
def my_saved(request):
    user = get_current_user(request)
    saved_listings = SavedListing.objects.filter(user=user).select_related('listing', 'listing__user')
    return render(request, 'core/my_saved.html', {'saved_listings': saved_listings})


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

@login_required_barter
def my_wishlist(request):
    user = get_current_user(request)
    wishlist_items = (
        WishlistItem.objects
        .filter(user=user, is_active=True)
        .annotate(match_count=Count('triggered_notifications'))
    )
    total_matches = sum(item.match_count for item in wishlist_items)
    return render(request, 'core/my_wishlist.html', {
        'wishlist_items': wishlist_items,
        'total_matches': total_matches,
    })


@login_required_barter
def wishlist_create(request):
    user = get_current_user(request)
    form = WishlistItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.user = user
        item.save()
        messages.success(request, 'Added to your wishlist.')
        return redirect('my_wishlist')
    return render(request, 'core/wishlist_form.html', {'form': form})


@login_required_barter
def wishlist_edit(request, pk):
    user = get_current_user(request)
    item = get_object_or_404(WishlistItem, pk=pk, user=user, is_active=True)
    form = WishlistItemForm(request.POST or None, instance=item)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Wishlist item updated.')
        return redirect('my_wishlist')
    return render(request, 'core/wishlist_form.html', {'form': form, 'item': item})


@login_required_barter
@require_POST
def wishlist_delete(request, pk):
    user = get_current_user(request)
    item = get_object_or_404(WishlistItem, pk=pk, user=user)
    item.is_active = False
    item.save()
    messages.info(request, 'Removed from wishlist.')
    return redirect('my_wishlist')


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@login_required_barter
def notifications_view(request):
    user = get_current_user(request)
    notifs = Notification.objects.filter(user=user)
    Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    return render(request, 'core/notifications.html', {'notifications': notifs})


@login_required_barter
def notification_click(request, pk):
    from django.utils import timezone
    user = get_current_user(request)
    notif = get_object_or_404(Notification, pk=pk, user=user)
    if not notif.clicked_at:
        notif.clicked_at = timezone.now()
        notif.is_read = True
        notif.save(update_fields=['clicked_at', 'is_read'])
    if notif.link:
        return redirect(notif.link)
    return redirect('notifications')
