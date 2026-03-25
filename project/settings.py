INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'apps.users',
]

import os

ALLOWED_HOSTS = ['*']

DEBUG = True
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

ROOT_URLCONF = 'project.urls'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',    # Vite dev server
    'http://localhost:5174',    # Alternative port
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
]

# Avoid silent POST redirects on API endpoints when slash is missing
APPEND_SLASH = False

STATIC_URL = '/static/'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bd',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': os.environ.get('DB_HOST', 'db'),  # Use 'db' by default (Docker), or env variable
        'PORT': '5432',
    }
}