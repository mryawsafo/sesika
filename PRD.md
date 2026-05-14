# Sesika – Product Requirements Document

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | Apr 2026 | MVP: phone login, single-photo listings, basic offer/contact reveal |
| v2.0 | May 2026 | Full platform spec: wishlist engine, AI enrichment, rentals, counteroffers, student verification, structured location, multi-photo, campus groups, trade ratings, offer timeouts |

---

## Overview

Sesika is a peer-to-peer barter marketplace for Ghana. Users trade items directly, adding cash top-ups when values don't perfectly match. The platform solves the double-coincidence-of-wants problem through a persistent wishlist with AI-powered matching.

---

## v2.0 Feature Set (current)

### Authentication & Profiles

**Phone-based OTP login**
- Login via WhatsApp number (Ghanaian numbers only)
- OTP sent via external WhatsApp OTP service
- Device token cookie for trusted devices (30-day expiry)
- Login attempts logged (IP, user-agent, success/fail)

**User profile**
- Display name, bio, WhatsApp number (separate from login number)
- Structured location: Region (16 Ghana regions), City/Town, Neighbourhood
- Contact reveal preference: `on_any_offer` (immediate) or `on_accepted_offer`
- Portfolio/Instagram URL, personal website URL
- Student badge (🎓) after verified university email
- Verified badge (✓) after phone OTP
- `completed_trades_count` computed from accepted offers
- Star rating average (from TradeRating records)

**Student email verification**
- Users submit a `.edu.gh` or recognised university domain email
- OTP sent via Django's email backend
- On success: Student badge activated, user joined to relevant CampusGroup
- Supported domains managed via `UniversityDomain` admin model

**Profile completion gate**
- New users redirected to `/profile/complete/` before accessing the platform
- Requires name + optional region/city

---

### Wishlist

**Purpose**: users list everything they would trade for. The minute a matching listing appears, they are notified. Designed to be the primary engagement and retention loop.

**Item fields**
- Title (what they want)
- Category (optional)
- Description (specific details)
- Want type: `acquire` (buy/trade) or `rent`
- Term type: `short_term` or `long_term` (urgency)
- Minimum acceptable condition: `any`, `fair_or_better`, `good_or_better`, `excellent_only`
- Size preference (optional free text)
- Max budget in GHS (optional)
- Notification frequency: `immediately`, `daily_digest`, `weekly_digest`

**Listing gate**
- First-time listers must add ≥ 3 wishlist items before creating their first listing
- Coaching message shown with progress (e.g. "2/3 added")

**Expiry**
- Default: 90 days (configurable in `SiteSettings`)
- User can renew for another full cycle via `/wishlist/<pk>/renew/`
- `expire_wishlist_items` management command marks expired items, sends notification

---

### Listings

**Transaction types**
- `trade` — swap items, cash top-ups allowed
- `rental` — lend item for a period, accept non-cash payment

**Listing types**
- `physical` — standard physical item
- `handmade` — user-made item (extra: `materials_used`)
- `service` — skill or labour offering (condition field hidden)

**Core fields**
- Title, category, subcategory (dynamic dropdown by category)
- Description
- Condition: `excellent`, `good`, `fair`, `for_parts` (hidden for services)
- User estimated value (GHS)
- Structured location: Region + City + Neighbourhood
- Want text (what the lister wants in exchange)
- Collection method: `pickup`, `delivery`, `both`
- Cash top-up direction: `willing_to_pay`, `requesting`, `open_to_both`, `cash_only`
- Listing behaviour: `permanent` or `temporary` (7 / 14 / 30 / 60 days)

**Physical/handmade extras**
- Brand, model name, size, colour, gender, materials_used

**Service extras**
- Service scope, delivery timeline (days), warranty offered, warranty duration, repair description

**Rental extras**
- Rental period unit (per hour / day / week / month / event)
- Payment accepted description
- Deposit required + description
- Availability notes
- Rental conditions (renters responsible for damage/loss — in terms of service)

**Photos**
- 1–3 photos required (enforced on create, optional replacement on edit)
- Multi-file upload via raw `<input type="file" multiple>`
- Stored via `ListingPhoto` model (separate from `Listing`)
- `primary_photo` property returns first photo; `all_photos` returns ordered queryset

**Valuation**
- User estimated value × condition multiplier (excellent=1.0, good=0.75, fair=0.5, for_parts=0.25)
- System estimated value from `CategoryBaseline` × multiplier
- Final value: 70% user + 30% system
- Market price field for scraped price data (populates when available)

**Listing behaviour**
- `permanent` — stays active until manually deleted/paused
- `temporary` — `expires_at` auto-set in `save()` based on `duration_days`
- Status: `pending_approval` → `active` → `traded` / `paused` / `expired`
- Owner can pause/resume active listings
- Admin approves listings (approval triggers AI enrichment)

**AI enrichment**
- Called on admin approval via `enrich_listing_with_ai(listing)` → OpenRouter (gpt-4o-mini)
- Stores JSON in `ai_enrichment` field: `summary`, `key_attributes`, `typical_use_cases`, `value_range_min/max`, `search_tags`
- Displayed on listing detail with disclaimer
- User can hide or flag for admin review
- Admin can manually edit enrichment (sets `ai_enrichment_admin_edited=True`, prevents auto-overwrite)
- `listing_stale_days` threshold in `SiteSettings`; management command can flag stale listings

---

### Offers

**Trade offer fields**
- Offered item description (optional if cash only)
- Offered item value (GHS, for suggestion calculation)
- Cash top-up (GHS)
- Message to seller

**Rental offer fields**
- Rental start date, end date
- Payment offered (free text)
- Message to owner

**State machine**
```
pending → accepted    (seller accepts)
pending → rejected    (seller rejects)
pending → countered   (seller sends counteroffer with counter_cash_topup + counter_message)
countered → accepted  (buyer accepts counter)
countered → rejected  (buyer rejects counter)
```

**Counteroffer**
- Seller can request a specific cash top-up amount + optional message
- Buyer sees counteroffer in "Sent" tab → Accept Counter or Decline
- Acceptance triggers contact reveal + listing marked `traded`

**Contact reveal**
- Controlled per user via `contact_reveal_preference`
- `on_any_offer`: contact revealed immediately when offer is submitted
- `on_accepted_offer`: contact revealed only on acceptance (or counter-acceptance)
- WhatsApp link: `https://wa.me/<number>?text=...` pre-filled

**Offer timeout**
- `check_offer_timeouts` management command fires after `offer_timeout_days` (default 3, configurable)
- Sends notification to listing owner to respond; sets `pending_timeout_notified_at` to avoid repeat

---

### AI Matching Engine

**match_listing_to_wishlists(listing)**
- Runs on every new active listing
- Embeds listing title+description, compares against all active wishlist items using OpenRouter
- Respects `want_type` ↔ `transaction_type` alignment
- Respects `condition_acceptable` threshold (CONDITION_ORDER dict)
- Tiers: Exact (≥ 0.90), Strong (0.75–0.89), Potential (0.55–0.74)
- Creates `Notification` with tier label and match score for each matched wishlist owner

**match_want_text_to_listings(wishlist_item)**
- Runs when a new wishlist item is saved
- Matches against all active listings
- Same tier scoring, same threshold (0.55)

**count_wishlist_demand(listing)**
- Returns count of active wishlist items that overlap with a listing
- Shown on listing detail as social proof ("X traders looking for this")

---

### Notifications

Types: `match_found`, `seller_demand`, `offer_received`, `offer_accepted`, `offer_rejected`, `offer_countered`, `offer_timeout`, `wishlist_expiring`, `listing_expiring`, `listing_stale`, `ai_section_updated`, `student_verified`, `trade_completed`, `rating_received`

Each notification stores: user, type, message, link, `is_read`, `clicked_at`, `match_tier`, optional `source_listing` FK.

---

### Trade Ratings

- Post-trade only (offer must be `accepted`)
- 1–5 stars + optional comment
- Each (rater, offer) pair unique — one rating per trade per user
- Displayed on profile (live rating average + recent reviews)
- Triggers `rating_received` notification

---

### Saved Listings

- Toggle save/unsave on any listing
- Bookmark icon on listing cards
- `/my/saved/` dashboard

---

### Campus Groups

- `UniversityDomain` admin model (domain, university name, active flag)
- `CampusGroup` model linked to domain
- `CampusMembership` created on successful student email verification
- Framework for campus-specific feed (future feature)

---

### Admin Portal (`/admin/`)

- `ListingAdmin`: photo inline, AI enrichment JSON display, approve action (triggers AI enrichment), clear_ai_flag action, ai_status field
- `SiteSettingsAdmin`: wishlist_default_expiry_days (90), offer_timeout_days (3), listing_stale_days (60)
- `UniversityDomainAdmin`, `CampusGroupAdmin`
- `TradeRatingAdmin`
- `OfferAdmin`: shows counter fields, pending_timeout_notified_at
- `NotificationAdmin`: shows match_tier

---

### Management Commands

| Command | Purpose |
|---------|---------|
| `expire_wishlist_items` | Marks expired wishlist items, sends renewal notifications |
| `check_offer_timeouts` | Notifies listing owners of pending offers older than `offer_timeout_days` |
| `create_admin` | Creates/resets superuser for Railway deploy-time |
| `seed_data` | Seeds CategoryBaseline records; optional `--listings` flag |

---

### Infrastructure

| Concern | Solution |
|---------|---------|
| Database (local) | SQLite |
| Database (production) | PostgreSQL via `dj-database-url` on Railway |
| Media storage | Cloudinary via `django-cloudinary-storage` |
| Static files | WhiteNoise |
| AI enrichment + matching | OpenRouter API (gpt-4o-mini) |
| Phone OTP | External WhatsApp OTP service (`FREE_OTP_SERVICE_URL`) |
| Student email OTP | Django `send_mail` |
| Price data | Category baselines seeded; market price field for scraped data |

---

### Key URLs

| URL | Auth | Notes |
|-----|------|-------|
| `/` | Public | Listings feed with category, type, region filters |
| `/login/` | — | Phone entry |
| `/otp/request/` | Logged in | WhatsApp OTP flow |
| `/profile/` | Logged in | Edit profile, student verify link, ratings |
| `/profile/complete/` | Logged in | First-time name + location |
| `/profile/student/verify/` | Logged in | Submit university email |
| `/profile/student/confirm/` | Logged in | Enter OTP code |
| `/listings/new/` | Verified | Wishlist gate (3 items required on first listing) |
| `/listings/<pk>/` | Public | Detail with photo gallery, AI section, offers |
| `/listings/<pk>/edit/` | Owner | |
| `/listings/<pk>/delete/` | Owner | POST only |
| `/listings/<pk>/pause/` | Owner | POST only, toggle |
| `/listings/<pk>/ai/hide/` | Owner | JSON POST |
| `/listings/<pk>/ai/flag/` | Owner | JSON POST |
| `/listings/<pk>/offer/` | Verified | Trade or rental offer form |
| `/offers/<pk>/success/` | Offer owner | Post-submit, shows WhatsApp or pending state |
| `/offers/<pk>/status/` | Party to offer | Accept / reject / counter / accept_counter / reject_counter |
| `/offers/<pk>/complete/` | Party to offer | Submit trade rating |
| `/offers/suggest/` | Public | JSON: suggested cash top-up range |
| `/my/listings/` | Logged in | |
| `/my/offers/` | Logged in | Sent + received tabs, counter modal, rating modal |
| `/my/saved/` | Logged in | |
| `/my/wishlist/` | Logged in | |
| `/my/notifications/` | Logged in | |
| `/wishlist/new/` | Logged in | |
| `/wishlist/<pk>/edit/` | Owner | |
| `/wishlist/<pk>/delete/` | Owner | POST only, soft-deletes |
| `/wishlist/<pk>/renew/` | Owner | POST only, resets expiry |
| `/about/` | Public | |
| `/privacy/` | Public | Rental liability disclaimer included |
| `/admin/` | Superuser | |

---

## What Is NOT in v2.0 (by design)

- In-app messaging / chat (planned for later)
- Payments or escrow
- Push notifications (WhatsApp / email notification engine framework exists, delivery not wired)
- Advanced search (text search, radius search)
- Campus community feed (groups model exists, feed not built)
- Public price index (price scraping runs internally, not exposed)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Active listings | 100+ |
| Wishlist items | 300+ |
| Offers made | 300+ |
| Contact reveals | 100+ |
| Conversion rate | reveals / offers |
| Wishlist-to-match rate | notifications triggered / wishlist items |
| Trade completion rate | accepted offers / total offers |
