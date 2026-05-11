import os
import sys
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create superuser from environment variables if one does not exist'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = os.environ.get('DJANGO_ADMIN_USER', 'admin')
        password = os.environ.get('DJANGO_ADMIN_PASSWORD')
        email = os.environ.get('DJANGO_ADMIN_EMAIL', '')

        print(f'[create_admin] DJANGO_ADMIN_USER={username}', flush=True)
        print(f'[create_admin] DJANGO_ADMIN_PASSWORD set: {bool(password)}', flush=True)

        if not password:
            print('[create_admin] ERROR: DJANGO_ADMIN_PASSWORD not set — admin not created.', file=sys.stderr, flush=True)
            return

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.save()
            print(f'[create_admin] Updated password for existing user "{username}".', flush=True)
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            print(f'[create_admin] Superuser "{username}" created.', flush=True)
