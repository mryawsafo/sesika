import json
import logging
import random
import string
import uuid
from decimal import Decimal
from django.db.models import Count, Avg

logger = logging.getLogger(__name__)

import requests as http_client
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    BarterUser, Listing, ListingPhoto, Offer, CategoryBaseline, CONDITION_MULTIPLIERS,
    CATEGORY_CHOICES, SUBCATEGORY_CHOICES, SavedListing, WishlistItem,
    Notification, match_listing_to_wishlists, match_want_text_to_listings,
    count_wishlist_demand, DeviceToken, LoginAttempt, UniversityDomain,
    CampusGroup, CampusMembership, TradeRating, enrich_listing_with_ai,
    validate_and_correct_listing_category, SiteSettings, GHANA_TOWNS,
)
from .forms import (
    LoginForm, ListingForm, OfferForm, WishlistItemForm, ProfileForm,
    CounterOfferForm,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_current_user(request):
    user_id = request.session.get('barter_user_id')
    if user_id:
        try:
            return BarterUser.objects.get(pk=user_id)
        except BarterUser.DoesNotExist:
            pass
    return None


def post_login_redirect(user):
    if not user.name:
        return 'complete_profile'
    return 'home'


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def login_required_barter(view_fn):
    def wrapper(request, *args, **kwargs):
        if not get_current_user(request):
            messages.warning(request, 'Please log in first.')
            return redirect('login')
        return view_fn(request, *args, **kwargs)
    wrapper.__name__ = view_fn.__name__
    return wrapper


def verified_required(view_fn):
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


def _generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def _should_reveal_contact(offer):
    """Return True if the offer sender's contact should be visible given listing owner's preference."""
    pref = offer.to_user.contact_reveal_preference
    if pref == 'on_any_offer':
        return True
    return offer.status == 'accepted'


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


def change_number(request):
    for key in ('barter_user_id', 'otp_whatsapp_url', 'otp_token', 'device_verified'):
        request.session.pop(key, None)
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
        region = request.POST.get('location_region', '').strip()
        city = request.POST.get('location_city', '').strip()
        if not name:
            error = 'Please enter your name.'
        else:
            user.name = name
            user.location_region = region
            user.location_city = city
            user.save()
            return redirect('home')

    from .models import GHANA_REGION_CHOICES
    return render(request, 'core/complete_profile.html', {
        'user': user,
        'error': error,
        'region_choices': GHANA_REGION_CHOICES,
        'towns_json': json.dumps(GHANA_TOWNS),
    })


@login_required_barter
def update_profile(request):
    user = get_current_user(request)
    form = ProfileForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    avg_rating = TradeRating.objects.filter(rated_user=user).aggregate(avg=Avg('score'))['avg']
    return render(request, 'core/profile.html', {
        'barter_user': user,
        'form': form,
        'avg_rating': avg_rating,
        'ratings': TradeRating.objects.filter(rated_user=user).select_related('rater').order_by('-created_at')[:10],
        'towns_json': json.dumps(GHANA_TOWNS),
    })


# ---------------------------------------------------------------------------
# Student email verification
# ---------------------------------------------------------------------------

@login_required_barter
def student_verify_request(request):
    user = get_current_user(request)
    error = None

    if request.method == 'POST':
        email = request.POST.get('student_email', '').strip().lower()
        if not email:
            error = 'Please enter your university email address.'
        else:
            domain = email.split('@')[-1] if '@' in email else ''
            if not UniversityDomain.objects.filter(domain=domain, is_active=True).exists():
                error = (
                    f'"{domain}" is not a recognised university domain. '
                    'If your university is missing, please contact us.'
                )
            else:
                otp = _generate_otp()
                request.session['student_otp'] = otp
                request.session['student_email_pending'] = email
                try:
                    send_mail(
                        subject='Sesika — Verify your student email',
                        message=(
                            f'Your Sesika student verification code is: {otp}\n\n'
                            'This code expires in 10 minutes. Do not share it.'
                        ),
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sesika.gh'),
                        recipient_list=[email],
                        fail_silently=False,
                    )
                    return redirect('student_verify_confirm')
                except Exception as e:
                    logger.error("Student email OTP send failed: %s", e)
                    error = 'Could not send verification email. Please try again.'

    domains = UniversityDomain.objects.filter(is_active=True).order_by('university_name')
    return render(request, 'core/student_verify.html', {
        'user': user,
        'error': error,
        'domains': domains,
    })


@login_required_barter
def student_verify_confirm(request):
    user = get_current_user(request)
    email = request.session.get('student_email_pending')
    if not email:
        return redirect('student_verify_request')

    error = None
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        expected = request.session.get('student_otp')
        if not code or code != expected:
            error = 'Incorrect code. Please try again.'
        else:
            user.student_email = email
            user.is_student_verified = True
            user.student_verified_at = timezone.now()
            user.save(update_fields=['student_email', 'is_student_verified', 'student_verified_at'])
            for key in ('student_otp', 'student_email_pending'):
                request.session.pop(key, None)

            domain = email.split('@')[-1]
            uni_domain = UniversityDomain.objects.filter(domain=domain).first()
            if uni_domain:
                for group in uni_domain.campus_groups.filter(is_active=True):
                    CampusMembership.objects.get_or_create(user=user, group=group)

            Notification.objects.create(
                user=user,
                type='student_verified',
                message=f'Student email verified: {email}. You now have a Student badge.',
                link='/profile/',
            )
            messages.success(request, '✅ Student email verified! Your Student badge is now active.')
            return redirect('profile')

    return render(request, 'core/student_verify_confirm.html', {
        'user': user,
        'email': email,
        'error': error,
    })


# ---------------------------------------------------------------------------
# Listing views
# ---------------------------------------------------------------------------

def home(request):
    listings = Listing.objects.filter(status='active').select_related('user').prefetch_related('photos')
    category_filter = request.GET.get('category', '')
    transaction_filter = request.GET.get('type', '')
    region_filter = request.GET.get('region', '')
    city_filter = request.GET.get('city', '')

    if category_filter:
        listings = listings.filter(category=category_filter)
    if transaction_filter in ('trade', 'rental'):
        listings = listings.filter(transaction_type=transaction_filter)
    if region_filter:
        listings = listings.filter(location_region=region_filter)
    if city_filter:
        listings = listings.filter(location_city__iexact=city_filter)

    current_user = get_current_user(request)
    saved_pks = set()
    if current_user:
        saved_pks = set(
            SavedListing.objects.filter(user=current_user)
            .values_list('listing_id', flat=True)
        )

    from .models import GHANA_REGION_CHOICES
    return render(request, 'core/home.html', {
        'listings': listings,
        'category_choices': CATEGORY_CHOICES,
        'region_choices': GHANA_REGION_CHOICES,
        'towns_json': json.dumps(GHANA_TOWNS),
        'selected_category': category_filter,
        'selected_type': transaction_filter,
        'selected_region': region_filter,
        'selected_city': city_filter,
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
    photos = listing.all_photos

    show_ai = (
        listing.ai_enrichment
        and not listing.ai_enrichment_hidden
    )

    return render(request, 'core/listing_detail.html', {
        'listing': listing,
        'photos': photos,
        'user_offer': user_offer,
        'is_owner': current_user and current_user.pk == listing.user.pk,
        'is_saved': is_saved,
        'demand_count': demand_count,
        'show_ai': show_ai,
        'contact_revealed': user_offer and _should_reveal_contact(user_offer),
    })


@verified_required
def listing_create(request):
    user = get_current_user(request)
    if not user.name:
        return redirect('complete_profile')

    # Wishlist gate: must have at least 3 active wishlist items before first listing
    wishlist_count = WishlistItem.objects.filter(user=user, is_active=True).count()
    existing_listings = Listing.objects.filter(user=user).exists()
    if not existing_listings and wishlist_count < 3:
        messages.info(
            request,
            f'Before listing your first item, please add at least 3 items to your wishlist '
            f'({wishlist_count}/3 added). This helps us find matches for you!'
        )
        return redirect('wishlist_create')

    form = ListingForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        listing = form.save(commit=False)
        listing.user = user
        listing.save()

        # Handle photos (min 1 required)
        photo_files = request.FILES.getlist('photos')
        if not photo_files:
            form.add_error('photos', 'Please upload at least 1 photo.')
            listing.delete()
            return render(request, 'core/listing_form.html', {
                'form': form,
                'action': 'Create',
                'subcategory_choices_json': json.dumps(SUBCATEGORY_CHOICES),
                'towns_json': json.dumps(GHANA_TOWNS),
            })

        for i, photo_file in enumerate(photo_files[:3], start=1):
            ListingPhoto.objects.create(listing=listing, image=photo_file, order=i)

        listing.compute_and_save_value()

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
        'towns_json': json.dumps(GHANA_TOWNS),
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

        new_photos = request.FILES.getlist('photos')
        if new_photos:
            listing.photos.all().delete()
            for i, photo_file in enumerate(new_photos[:3], start=1):
                ListingPhoto.objects.create(listing=listing, image=photo_file, order=i)

        listing.compute_and_save_value()
        messages.success(request, 'Listing updated.')
        return redirect('listing_detail', pk=listing.pk)

    return render(request, 'core/listing_form.html', {
        'form': form,
        'action': 'Edit',
        'listing': listing,
        'existing_photos': listing.all_photos,
        'subcategory_choices_json': json.dumps(SUBCATEGORY_CHOICES),
        'towns_json': json.dumps(GHANA_TOWNS),
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


@verified_required
@require_POST
def listing_pause_toggle(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    user = get_current_user(request)

    if listing.user.pk != user.pk:
        messages.error(request, 'You can only manage your own listings.')
        return redirect('listing_detail', pk=pk)

    if listing.status == 'active':
        listing.status = 'paused'
        listing.save(update_fields=['status'])
        messages.info(request, 'Listing paused. It won\'t appear in matches until you resume it.')
    elif listing.status == 'paused':
        listing.status = 'active'
        listing.save(update_fields=['status'])
        messages.success(request, 'Listing resumed.')

    return redirect('listing_detail', pk=pk)


# ---------------------------------------------------------------------------
# AI enrichment actions (user-facing)
# ---------------------------------------------------------------------------

@login_required_barter
@require_POST
def listing_ai_hide(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    user = get_current_user(request)
    if listing.user.pk != user.pk:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    listing.ai_enrichment_hidden = True
    listing.save(update_fields=['ai_enrichment_hidden'])
    return JsonResponse({'status': 'hidden'})


@login_required_barter
@require_POST
def listing_ai_flag(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    user = get_current_user(request)
    if listing.user.pk != user.pk:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    listing.ai_enrichment_flagged = True
    listing.save(update_fields=['ai_enrichment_flagged'])
    return JsonResponse({'status': 'flagged'})


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
            offer_type=listing.transaction_type,
            offered_item_description=form.cleaned_data.get('offered_item_description', ''),
            cash_topup=cash_topup,
            message=form.cleaned_data.get('message', ''),
            rental_start_date=form.cleaned_data.get('rental_start_date'),
            rental_end_date=form.cleaned_data.get('rental_end_date'),
            rental_payment_offered=form.cleaned_data.get('rental_payment_offered', ''),
        )
        offer.compute_suggested_topup(offered_value + cash_topup)

        if listing.user.contact_reveal_preference == 'on_any_offer':
            offer.contact_revealed = True

        offer.save()

        Notification.objects.create(
            user=listing.user,
            type='offer_received',
            message=f'You have a new offer on "{listing.title}" from {user.name or user.phone}.',
            link=f'/my/offers/',
            source_listing=listing,
        )

        messages.success(request, '🎉 Offer submitted!')
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

    contact_revealed = _should_reveal_contact(offer)
    whatsapp_link = offer.whatsapp_link() if contact_revealed else None

    return render(request, 'core/offer_success.html', {
        'offer': offer,
        'contact_revealed': contact_revealed,
        'whatsapp_link': whatsapp_link,
    })


def offer_suggest(request):
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
    listings = Listing.objects.filter(user=user).order_by('-created_at').prefetch_related('photos')
    return render(request, 'core/my_listings.html', {'listings': listings})


@login_required_barter
@require_POST
def offer_update_status(request, offer_pk):
    user = get_current_user(request)
    offer = get_object_or_404(Offer, pk=offer_pk)
    if offer.to_user.pk != user.pk and offer.from_user.pk != user.pk:
        messages.error(request, 'Access denied.')
        return redirect('my_offers')
    action = request.POST.get('action')

    if offer.status == 'pending':
        if action == 'accept':
            offer.status = 'accepted'
            offer.contact_revealed = True
            offer.save()
            offer.listing.status = 'traded'
            offer.listing.save(update_fields=['status'])
            messages.success(request, f'Offer accepted. {offer.from_user.name or offer.from_user.phone} can now contact you.')
            Notification.objects.create(
                user=offer.from_user,
                type='offer_accepted',
                message=f'Your offer on "{offer.listing.title}" was accepted! Contact the seller.',
                link=f'/offers/{offer.pk}/success/',
            )

        elif action == 'reject':
            offer.status = 'rejected'
            offer.save(update_fields=['status'])
            messages.info(request, 'Offer rejected.')
            Notification.objects.create(
                user=offer.from_user,
                type='offer_rejected',
                message=f'Your offer on "{offer.listing.title}" was not accepted.',
                link=f'/listings/{offer.listing.pk}/',
            )

        elif action == 'counter':
            form = CounterOfferForm(request.POST)
            if form.is_valid():
                offer.status = 'countered'
                offer.counter_cash_topup = form.cleaned_data['counter_cash_topup']
                offer.counter_message = form.cleaned_data.get('counter_message', '')
                offer.save(update_fields=['status', 'counter_cash_topup', 'counter_message'])
                messages.info(request, 'Counteroffer sent.')
                Notification.objects.create(
                    user=offer.from_user,
                    type='offer_countered',
                    message=(
                        f'"{offer.listing.title}": the seller has sent a counteroffer requesting '
                        f'GHS {offer.counter_cash_topup:.0f} top-up.'
                    ),
                    link='/my/offers/',
                    source_listing=offer.listing,
                )

    elif offer.status == 'countered' and offer.from_user.pk == user.pk:
        if action == 'accept_counter':
            offer.status = 'accepted'
            offer.contact_revealed = True
            offer.save(update_fields=['status', 'contact_revealed'])
            offer.listing.status = 'traded'
            offer.listing.save(update_fields=['status'])
            messages.success(request, 'Counteroffer accepted. Trade confirmed!')
            Notification.objects.create(
                user=offer.to_user,
                type='offer_accepted',
                message=f'{offer.from_user.name or offer.from_user.phone} accepted your counteroffer on "{offer.listing.title}".',
                link='/my/offers/',
            )

        elif action == 'reject_counter':
            offer.status = 'rejected'
            offer.save(update_fields=['status'])
            messages.info(request, 'Counteroffer declined.')
            Notification.objects.create(
                user=offer.to_user,
                type='offer_rejected',
                message=f'{offer.from_user.name or offer.from_user.phone} declined your counteroffer on "{offer.listing.title}".',
                link='/my/offers/',
            )

    return redirect('my_offers')


@login_required_barter
def my_offers(request):
    user = get_current_user(request)
    offers_made = Offer.objects.filter(from_user=user).select_related('listing', 'to_user').prefetch_related('listing__photos')
    offers_received = Offer.objects.filter(to_user=user).select_related('listing', 'from_user').prefetch_related('listing__photos')
    counter_form = CounterOfferForm()
    return render(request, 'core/my_offers.html', {
        'offers_made': offers_made,
        'offers_received': offers_received,
        'counter_form': counter_form,
    })


# ---------------------------------------------------------------------------
# Trade completion and ratings
# ---------------------------------------------------------------------------

@login_required_barter
@require_POST
def trade_complete(request, offer_pk):
    user = get_current_user(request)
    offer = get_object_or_404(Offer, pk=offer_pk, status='accepted')

    if offer.from_user.pk != user.pk and offer.to_user.pk != user.pk:
        messages.error(request, 'Access denied.')
        return redirect('my_offers')

    other_user = offer.to_user if offer.from_user.pk == user.pk else offer.from_user
    score = int(request.POST.get('score', 0))
    comment = request.POST.get('comment', '').strip()

    if score < 1 or score > 5:
        messages.error(request, 'Please select a rating from 1 to 5.')
        return redirect('my_offers')

    rating, created = TradeRating.objects.get_or_create(
        rater=user,
        offer=offer,
        defaults={'rated_user': other_user, 'score': score, 'comment': comment},
    )
    if not created:
        messages.info(request, 'You have already rated this trade.')
        return redirect('my_offers')

    Notification.objects.create(
        user=other_user,
        type='rating_received',
        message=f'{user.name or user.phone} left you a {score}/5 rating for the "{offer.listing.title}" trade.',
        link='/profile/',
    )
    offer.listing.status = 'traded'
    offer.listing.save(update_fields=['status'])
    messages.success(request, '⭐ Trade rated. Thank you!')
    return redirect('my_offers')


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
    saved_listings = SavedListing.objects.filter(user=user).select_related('listing', 'listing__user').prefetch_related('listing__photos')
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
        'has_enough': wishlist_items.count() >= 3,
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

        wishlist_count = WishlistItem.objects.filter(user=user, is_active=True).count()
        if wishlist_count < 3:
            messages.info(request, f'Add {3 - wishlist_count} more item(s) to unlock listing.')
            return redirect('wishlist_create')
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
    item.save(update_fields=['is_active'])
    messages.info(request, 'Removed from wishlist.')
    return redirect('my_wishlist')


@login_required_barter
@require_POST
def wishlist_renew(request, pk):
    """Reset expiry on a wishlist item for another full cycle."""
    user = get_current_user(request)
    item = get_object_or_404(WishlistItem, pk=pk, user=user)
    from datetime import timedelta
    days = SiteSettings.get().wishlist_default_expiry_days
    item.expires_at = timezone.now() + timedelta(days=days)
    item.is_active = True
    item.save(update_fields=['expires_at', 'is_active'])
    messages.success(request, f'Wishlist item renewed for {days} more days.')
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
    user = get_current_user(request)
    notif = get_object_or_404(Notification, pk=pk, user=user)
    if not notif.clicked_at:
        notif.clicked_at = timezone.now()
        notif.is_read = True
        notif.save(update_fields=['clicked_at', 'is_read'])
    if notif.link:
        return redirect(notif.link)
    return redirect('notifications')


# ---------------------------------------------------------------------------
# Static pages
# ---------------------------------------------------------------------------

def about(request):
    return render(request, 'core/about.html')


def privacy(request):
    return render(request, 'core/privacy.html')


# ---------------------------------------------------------------------------
# Admin seeding tool
# ---------------------------------------------------------------------------

def admin_seed_listing(request):
    if not request.user.is_staff:
        return redirect('/admin/login/?next=/admin-tools/seed/')

    from .models import (
        CATEGORY_CHOICES, CONDITION_CHOICES, GHANA_REGION_CHOICES,
        TRANSACTION_TYPE_CHOICES, LISTING_TYPE_CHOICES, CONTACT_REVEAL_CHOICES,
    )

    success = None
    error = None
    created_listing = None

    if request.method == 'POST':
        phone_raw = request.POST.get('phone', '').strip().replace(' ', '').replace('-', '')
        if phone_raw.startswith('0') and len(phone_raw) == 10:
            phone = f'+233{phone_raw[1:]}'
        elif phone_raw.startswith('+233'):
            phone = phone_raw
        elif phone_raw.startswith('233'):
            phone = f'+{phone_raw}'
        else:
            phone = phone_raw

        name             = request.POST.get('name', '').strip()
        title            = request.POST.get('title', '').strip()
        contact_pref     = request.POST.get('contact_reveal_preference', 'on_any_offer')

        if not phone or not title:
            error = 'Phone number and title are required.'
        else:
            user, created = BarterUser.objects.get_or_create(
                phone=phone,
                defaults={'name': name, 'is_verified': True, 'contact_reveal_preference': contact_pref},
            )
            if not created:
                update_fields = []
                if name and not user.name:
                    user.name = name
                    update_fields.append('name')
                user.contact_reveal_preference = contact_pref
                update_fields.append('contact_reveal_preference')
                user.save(update_fields=update_fields)

            listing = Listing(
                user=user,
                title=title,
                transaction_type=request.POST.get('transaction_type', 'trade'),
                listing_type=request.POST.get('listing_type', 'physical'),
                category=request.POST.get('category', 'other'),
                subcategory=request.POST.get('subcategory', ''),
                condition=request.POST.get('condition', 'good'),
                description=request.POST.get('description', ''),
                want_text=request.POST.get('want_text', ''),
                user_estimated_value=request.POST.get('user_estimated_value') or 0,
                location_region=request.POST.get('location_region', ''),
                location_city=request.POST.get('location_city', ''),
                location_neighbourhood=request.POST.get('location_neighbourhood', ''),
                brand=request.POST.get('brand', ''),
                model_name=request.POST.get('model_name', ''),
                size=request.POST.get('size', ''),
                colour=request.POST.get('colour', ''),
                listing_behaviour='permanent',
                status='active',
            )
            listing.save()

            photo_files = request.FILES.getlist('photos')
            for i, f in enumerate(photo_files[:3], start=1):
                ListingPhoto.objects.create(listing=listing, image=f, order=i)

            listing.compute_and_save_value()
            created_listing = listing
            success = f'Listing "{listing.title}" created for {user.name or user.phone} (pk={listing.pk})'

    return render(request, 'core/admin_seed_listing.html', {
        'success': success,
        'error': error,
        'created_listing': created_listing,
        'category_choices': CATEGORY_CHOICES,
        'condition_choices': CONDITION_CHOICES,
        'region_choices': GHANA_REGION_CHOICES,
        'transaction_type_choices': TRANSACTION_TYPE_CHOICES,
        'listing_type_choices': LISTING_TYPE_CHOICES,
        'subcategory_choices_json': json.dumps(SUBCATEGORY_CHOICES),
        'contact_reveal_choices': CONTACT_REVEAL_CHOICES,
        'towns_json': json.dumps(GHANA_TOWNS),
    })
