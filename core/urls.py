from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('otp/request/', views.request_otp, name='request_otp'),
    path('otp/verify/', views.verify_otp, name='verify_otp'),
    path('profile/', views.update_profile, name='update_profile'),
    path('profile/complete/', views.complete_profile, name='complete_profile'),

    # Listings
    path('listings/new/', views.listing_create, name='listing_create'),
    path('listings/<int:pk>/', views.listing_detail, name='listing_detail'),
    path('listings/<int:pk>/edit/', views.listing_edit, name='listing_edit'),
    path('listings/<int:pk>/delete/', views.listing_delete, name='listing_delete'),

    # Offers
    path('listings/<int:listing_pk>/offer/', views.offer_create, name='offer_create'),
    path('offers/<int:offer_pk>/success/', views.offer_success, name='offer_success'),
    path('offers/suggest/', views.offer_suggest, name='offer_suggest'),

    # My stuff
    path('my/listings/', views.my_listings, name='my_listings'),
    path('my/offers/', views.my_offers, name='my_offers'),
    path('offers/<int:offer_pk>/status/', views.offer_update_status, name='offer_update_status'),

    # Saved listings
    path('listings/<int:pk>/save/', views.listing_save_toggle, name='listing_save_toggle'),
    path('my/saved/', views.my_saved, name='my_saved'),

    # Wishlist
    path('my/wishlist/', views.my_wishlist, name='my_wishlist'),
    path('wishlist/new/', views.wishlist_create, name='wishlist_create'),
    path('wishlist/<int:pk>/edit/', views.wishlist_edit, name='wishlist_edit'),
    path('wishlist/<int:pk>/delete/', views.wishlist_delete, name='wishlist_delete'),

    # Notifications
    path('my/notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/go/', views.notification_click, name='notification_click'),
]
