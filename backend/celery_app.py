# Simple import to use the celery instance from tasks.py
from tasks import celery, generate_parking_report

# This makes the celery instance available when importing celery_app
# The worker command will use: celery -A celery_app worker --loglevel=info
