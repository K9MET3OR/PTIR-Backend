"""
Local development settings - SQLite (rápido para testes)
Use: python manage.py migrate --settings=settings_local
     python manage.py runserver --settings=settings_local
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'apps.users',
]

ALLOWED_HOSTS = ['*']
ROOT_URLCONF = 'project.urls'
SECRET_KEY = 'dev-secret-key-insecure-change-in-production'

# SQLite - sem necessidade de PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

from apps.users.models import User
User.objects.create(username='gestor', email='gestor@hermez.com', name='Gestor Test', role='gestor')
User.objects.create(username='motorista', email='motorista33@hermez.com', name='Motorista Test', role='motorista')
User.objects.create(username='cliente', email='client666@hermez.com', name='Cliente Test', role='cliente')
exit()
