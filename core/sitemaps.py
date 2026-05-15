from django.contrib.sitemaps import Sitemap
from .models import Listing


class ListingSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Listing.objects.filter(status='active').order_by('-created_at')

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return f'/listings/{obj.pk}/'
