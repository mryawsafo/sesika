import os
import tempfile
import urllib.request

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

import requests

from core.models import Listing


class Command(BaseCommand):
    help = 'Fetch images from Google Custom Search for listings that have no image.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--listing-ids',
            nargs='+',
            type=int,
            dest='listing_ids',
            help='Specific listing PKs to process (default: all without images)',
        )

    def handle(self, *args, **options):
        api_key = getattr(settings, 'GOOGLE_IMAGE_API_KEY', None)
        cx = getattr(settings, 'GOOGLE_SEARCH_CX', None)

        if not api_key or not cx:
            self.stderr.write(
                'GOOGLE_IMAGE_API_KEY and GOOGLE_SEARCH_CX must be set in settings / .env'
            )
            return

        ids = options.get('listing_ids')
        qs = Listing.objects.filter(image='') if not ids else Listing.objects.filter(pk__in=ids, image='')

        if not qs.exists():
            self.stdout.write('No listings without images found.')
            return

        for listing in qs:
            query = f"{listing.title} {listing.category}"
            self.stdout.write(f'Searching: {query}')

            try:
                resp = requests.get(
                    'https://www.googleapis.com/customsearch/v1',
                    params={
                        'key': api_key,
                        'cx': cx,
                        'q': query,
                        'searchType': 'image',
                        'num': 1,
                        'safe': 'active',
                        'imgSize': 'medium',
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                items = resp.json().get('items', [])
            except Exception as exc:
                self.stderr.write(f'  Search failed for listing {listing.pk}: {exc}')
                continue

            if not items:
                self.stdout.write(f'  No results for listing {listing.pk}')
                continue

            image_url = items[0].get('link')
            if not image_url:
                continue

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                    req = urllib.request.Request(
                        image_url,
                        headers={'User-Agent': 'Mozilla/5.0'},
                    )
                    with urllib.request.urlopen(req, timeout=10) as r:
                        tmp.write(r.read())
                    tmp_path = tmp.name

                filename = f'listing_{listing.pk}_auto.jpg'
                with open(tmp_path, 'rb') as f:
                    listing.image.save(filename, File(f), save=True)

                os.unlink(tmp_path)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Saved image for listing {listing.pk}: {listing.title}'))
            except Exception as exc:
                self.stderr.write(f'  Download failed for listing {listing.pk}: {exc}')
