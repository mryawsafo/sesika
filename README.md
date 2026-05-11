# Sesika – MVP

A lean barter/trade marketplace for Ghana. Built with Django + SQLite.

---

## Project Structure

```
barter_mvp/
├── manage.py
├── requirements.txt
├── db.sqlite3              ← created on first migrate
├── static/
├── barter_mvp/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── core/
    ├── models.py           ← BarterUser, Listing, Offer, OTPCode, CategoryBaseline
    ├── views.py            ← All views (auth, listings, offers)
    ├── forms.py            ← LoginForm, OTPVerifyForm, ListingForm, OfferForm
    ├── urls.py             ← All URL patterns
    ├── admin.py
    ├── apps.py
    ├── context_processors.py
    ├── management/
    │   └── commands/
    │       └── seed_data.py
    └── templates/core/
        ├── base.html
        ├── home.html
        ├── login.html
        ├── request_otp.html
        ├── verify_otp.html
        ├── profile.html
        ├── listing_form.html     ← create + edit
        ├── listing_detail.html
        ├── offer_form.html       ← with live suggestion JS
        ├── offer_success.html
        ├── my_listings.html
        └── my_offers.html
```

---

## Quickstart

### 1. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Seed category baselines (required for valuation logic)

```bash
python manage.py seed_data
```

Optionally seed 5 sample listings too:

```bash
python manage.py seed_data --listings
```

### 5. Create a Django superuser (to access /admin)

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000

---

## User Flows

### Registration & Verification
1. Go to `/login/` → enter phone number (e.g. `+233201234567`)
2. Click **Generate My OTP Code** → your 6-digit code appears on screen
3. Click **Enter Code Now** → type the code → verified ✅

> In development the OTP is shown directly on screen. In production you'd
> integrate a real WhatsApp Business API (e.g. Twilio, Vonage) to send the
> code programmatically.

### Create a Listing
1. Must be verified
2. Click **+ List Item** in the nav
3. Fill in the form → system auto-computes `final_estimated_value`
4. Formula: `final = (user_value × condition_multiplier × 0.7) + (baseline × condition_multiplier × 0.3)`

### Browse & Make an Offer
1. Browse listings on the homepage, filter by category
2. Click a listing → **Make Offer →**
3. Fill offer form (item description + cash top-up)
4. As you type, suggested cash range updates live via `/offers/suggest/`
5. Submit → WhatsApp contact unlocked → redirect to `/offers/<id>/success/`

### Unlock Contact
After submitting an offer the seller's WhatsApp link is shown:
```
https://wa.me/<number>?text=Hi%2C+I+saw+your+listing+for+...
```

---

## Key Endpoints

| URL | View | Auth |
|-----|------|------|
| `/` | Listings feed | Public |
| `/login/` | Phone login | — |
| `/otp/request/` | Generate OTP | Logged in |
| `/otp/verify/` | Enter OTP | Logged in |
| `/listings/new/` | Create listing | Verified |
| `/listings/<pk>/` | Listing detail | Public |
| `/listings/<pk>/edit/` | Edit listing | Owner |
| `/listings/<pk>/delete/` | Delete listing | Owner |
| `/listings/<pk>/offer/` | Make offer | Verified |
| `/offers/<pk>/success/` | Unlock WhatsApp | Offer owner |
| `/offers/suggest/` | Cash suggestion API | Public (JSON) |
| `/my/listings/` | My listings | Logged in |
| `/my/offers/` | My offers | Logged in |
| `/admin/` | Django admin | Superuser |

---

## Core Logic

### Listing Valuation
```python
multiplier = {'new': 1.0, 'used': 0.7, 'old': 0.5}[condition]
user_val   = user_estimated_value × multiplier
system_val = category_baseline.typical_value × multiplier
final      = (user_val × 0.7) + (system_val × 0.3)
```

### Offer Suggestion
```python
diff        = listing.final_estimated_value − (offered_item_value + cash_topup)
suggest_min = diff × 0.8
suggest_max = diff × 1.2
```

### OTP
- 6-digit numeric code
- Expires in 10 minutes
- Old codes invalidated on new request
- `is_verified` set to `True` on successful entry

---

## Deployment with Cloudflare Tunnel

1. Install `cloudflared`
2. `python manage.py runserver 0.0.0.0:8000`
3. `cloudflared tunnel --url http://localhost:8000`
4. Add the tunnel URL to `ALLOWED_HOSTS` in `settings.py`

---

## What's NOT in this MVP (by design)

- ❌ Chat / messaging
- ❌ Payments or escrow
- ❌ Push notifications
- ❌ Ratings & reviews
- ❌ Image file upload (URL only)
- ❌ Advanced search/matching
- ❌ Admin dashboard customisation

## Success Criteria (from PRD)

- 100 active listings
- 300 offers made
- 100 contact reveals
- `conversion_rate = reveals / offers`
