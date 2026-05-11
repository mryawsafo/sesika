import re
import time
from datetime import timedelta
from decimal import Decimal

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import PriceSample

JIJI_CATEGORY_URLS = {
    'phones_tablets': ['/mobile-phones'],
    'computers':      ['/computers-and-laptops'],
    'electronics':    ['/electronics', '/tv-dvd-equipment', '/audio-and-music-equipment'],
    'gaming':         ['/video-games-and-consoles'],
    'vehicles':       ['/cars', '/motorcycles-and-scooters'],
    'fashion':        ['/mens-fashion', '/womens-fashion'],
    'home_furniture': ['/furniture', '/home-appliances'],
    'health_beauty':  ['/health-and-beauty'],
    'sports_hobbies': ['/hobbies-art-sport'],
    'tools_equipment':['/tools-accessories'],
}

PAGES_PER_URL = 5
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; Sesika/1.0)'}
TITLE_RE = re.compile(r'qa-advert-title[^>]*>([^<]{5,150})')
PRICE_RE = re.compile(r'qa-advert-price[^>]*>\s*GH[₵C]\s*([\d,]+)')


class Command(BaseCommand):
    help = 'Scrape Jiji Ghana for price samples across all categories (run weekly via cron)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category', type=str, default=None,
            help='Scrape a single category only (e.g. phones_tablets)',
        )

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=30)
        deleted, _ = PriceSample.objects.filter(scraped_at__lt=cutoff).delete()
        self.stdout.write(f'Purged {deleted} stale samples.')

        target = options['category']
        targets = {target: JIJI_CATEGORY_URLS[target]} if target else JIJI_CATEGORY_URLS

        total = 0
        for category, url_paths in targets.items():
            cat_count = 0
            for url_path in url_paths:
                for page in range(1, PAGES_PER_URL + 1):
                    url = f'https://jiji.com.gh{url_path}?page={page}'
                    try:
                        resp = requests.get(url, timeout=10, headers=HEADERS)
                        if resp.status_code != 200:
                            break
                        titles = TITLE_RE.findall(resp.text)
                        prices_raw = PRICE_RE.findall(resp.text)
                        pairs = list(zip(titles, prices_raw))
                        if not pairs:
                            break
                        PriceSample.objects.bulk_create([
                            PriceSample(
                                title=title.strip(),
                                price_ghs=Decimal(price.replace(',', '')),
                                category=category,
                            )
                            for title, price in pairs
                        ])
                        cat_count += len(pairs)
                        time.sleep(0.5)
                    except Exception as exc:
                        self.stderr.write(f'  Error {url}: {exc}')
                        break

            self.stdout.write(f'  {category}: {cat_count} samples saved')
            total += cat_count

        self.stdout.write(self.style.SUCCESS(f'Done. {total} total samples saved.'))
