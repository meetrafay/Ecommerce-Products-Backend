import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'product_api.settings')

app = Celery('product_api')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()