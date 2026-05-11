web: python manage.py migrate --run-syncdb && python manage.py create_admin && python manage.py collectstatic --noinput && gunicorn barter_mvp.wsgi --workers 2 --log-file -
