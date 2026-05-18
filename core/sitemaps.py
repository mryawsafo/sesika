from django.contrib.sitemaps import Sitemap
from .models import Listing


class ListingSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Listing.objects.filter(status='active', slug__gt='').order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/listings/{obj.slug}/'
