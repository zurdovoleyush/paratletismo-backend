release: python manage.py migrate
web: gunicorn paratletismo_core.wsgi --bind 0.0.0.0:$PORT --workers 2 --threads 2
