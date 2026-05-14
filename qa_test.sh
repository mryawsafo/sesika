#!/usr/bin/env bash
# Sesika – End-to-End QA Test Script
# Usage: ./qa_test.sh [base_url]
# Requires Django dev server running on base_url (default: http://localhost:8000)

BASE="${1:-http://localhost:8000}"
PASS=0
FAIL=0

G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; N='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$SCRIPT_DIR/venv/bin/python"
MANAGE_CMD="$PYTHON $SCRIPT_DIR/manage.py"

section() { printf "\n${Y}── %s ──${N}\n" "$1"; }

check() {
  local label="$1" expected="$2" url="$3"
  shift 3
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" "$@" "$url")
  if [ "$status" = "$expected" ]; then
    printf "  ${G}PASS${N} [%s] %s\n" "$status" "$label"
    PASS=$((PASS+1))
  else
    printf "  ${R}FAIL${N} [%s expected %s] %s\n" "$status" "$expected" "$label"
    FAIL=$((FAIL+1))
  fi
}

# ── Setup ──────────────────────────────────────────────────────────────────────

section "Setup: creating test data"

SETUP_OUTPUT=$("$PYTHON" "$SCRIPT_DIR/manage.py" shell 2>/dev/null << 'PYEOF'
from core.models import BarterUser, WishlistItem, Listing, CATEGORY_CHOICES
from django.contrib.sessions.backends.db import SessionStore

# Seller
seller, _ = BarterUser.objects.get_or_create(
    phone='+233200000001',
    defaults={'name':'QA Seller','location_city':'Accra','location_region':'ga','is_verified':True}
)
# 3 wishlist items (needed to pass listing gate)
for i in range(3):
    WishlistItem.objects.get_or_create(
        user=seller, title=f'QA Wishlist {i+1}',
        defaults={'want_type':'acquire','term_type':'short_term'}
    )
# One listing per category
cat_list = [c[0] for c in CATEGORY_CHOICES]
for cat in cat_list:
    Listing.objects.get_or_create(
        user=seller, category=cat, title=f'QA {cat}',
        defaults={
            'transaction_type':'trade','listing_type':'physical',
            'condition':'good','description':f'QA listing {cat}',
            'want_text':'Anything','user_estimated_value':100,
            'location_region':'ga','location_city':'Accra',
            'listing_behaviour':'permanent','status':'active',
        }
    )
first_listing = Listing.objects.filter(user=seller, status='active').first()

# Buyer
buyer, _ = BarterUser.objects.get_or_create(
    phone='+233200000002',
    defaults={'name':'QA Buyer','location_city':'Kumasi','location_region':'ah','is_verified':True}
)

# Sessions
def make_session(user):
    s = SessionStore()
    s['barter_user_id'] = user.pk
    s['device_verified'] = True
    s.create()
    return s.session_key

seller_key = make_session(seller)
buyer_key  = make_session(buyer)

print(f"SELLER_PK={seller.pk}")
print(f"BUYER_PK={buyer.pk}")
print(f"SELLER_SESSION={seller_key}")
print(f"BUYER_SESSION={buyer_key}")
print(f"LISTING_PK={first_listing.pk if first_listing else 0}")
PYEOF
)

eval "$(echo "$SETUP_OUTPUT" | grep -E '^(SELLER_PK|BUYER_PK|SELLER_SESSION|BUYER_SESSION|LISTING_PK)=')"
echo "  Seller PK: $SELLER_PK  Buyer PK: $BUYER_PK  Listing PK: $LISTING_PK"
SC="-b sessionid=$SELLER_SESSION"
BC="-b sessionid=$BUYER_SESSION"

# ── Public pages ───────────────────────────────────────────────────────────────

section "Public pages (no auth)"
check "Home"                        200 "$BASE/"
check "Login"                       200 "$BASE/login/"
check "About"                       200 "$BASE/about/"
check "Privacy"                     200 "$BASE/privacy/"
check "404 on missing listing"      404 "$BASE/listings/999999/"

section "Category / type / region filters"
check "Category filter"             200 "$BASE/?category=electronics"
check "Type=rental filter"          200 "$BASE/?type=rental"
check "Region filter"               200 "$BASE/?region=ga"
check "Combined filters"            200 "$BASE/?category=electronics&type=trade&region=ga"

section "Listing detail (public)"
if [ "$LISTING_PK" != "0" ]; then
  check "Listing detail"            200 "$BASE/listings/$LISTING_PK/"
fi

# ── Anon redirects ─────────────────────────────────────────────────────────────

section "Unauthenticated redirects → /login/"
check "My listings (anon)"         302 "$BASE/my/listings/"
check "My offers (anon)"           302 "$BASE/my/offers/"
check "My wishlist (anon)"         302 "$BASE/my/wishlist/"
check "My saved (anon)"            302 "$BASE/my/saved/"
check "Notifications (anon)"       302 "$BASE/my/notifications/"
check "Profile (anon)"             302 "$BASE/profile/"
check "Wishlist new (anon)"        302 "$BASE/wishlist/new/"
check "Listing new (anon)"         302 "$BASE/listings/new/"

# ── Authenticated pages ────────────────────────────────────────────────────────

section "Authenticated pages (seller session)"
check "Home (authed)"               200 "$BASE/"                              $SC
check "My listings"                 200 "$BASE/my/listings/"                  $SC
check "My offers"                   200 "$BASE/my/offers/"                    $SC
check "My wishlist"                 200 "$BASE/my/wishlist/"                  $SC
check "My saved"                    200 "$BASE/my/saved/"                     $SC
check "Notifications"               200 "$BASE/my/notifications/"             $SC
check "Profile"                     200 "$BASE/profile/"                      $SC
check "Wishlist create form"        200 "$BASE/wishlist/new/"                 $SC
check "Listing create form"         200 "$BASE/listings/new/"                 $SC
check "Student verify form"         200 "$BASE/profile/student/verify/"       $SC

if [ "$LISTING_PK" != "0" ]; then
  check "Listing edit (owner)"      200 "$BASE/listings/$LISTING_PK/edit/"    $SC
fi

# ── Offer flow ─────────────────────────────────────────────────────────────────

section "Offer flow (buyer session)"
if [ "$LISTING_PK" != "0" ]; then
  check "Offer form (buyer)"        200 "$BASE/listings/$LISTING_PK/offer/"   $BC
fi

# ── Ownership guard ────────────────────────────────────────────────────────────

section "Ownership guard"
if [ "$LISTING_PK" != "0" ]; then
  # Owner should be redirected away from their own offer form
  check "Owner blocked from own offer" 302 "$BASE/listings/$LISTING_PK/offer/" $SC
fi

# ── Summary ────────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════"
printf "  Results: ${G}%d passed${N}  ${R}%d failed${N}\n" "$PASS" "$FAIL"
echo "════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Server log (errors only):"
  grep -E "Error|500|Traceback" /tmp/django_server.log 2>/dev/null | tail -20 || true
  exit 1
else
  printf "\n  ${G}All %d tests passed.${N}\n\n" "$PASS"
  exit 0
fi
