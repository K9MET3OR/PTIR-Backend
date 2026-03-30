INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'corsheaders',
    'rest_framework',
    'apps.user.apps.UserConfig',
    'apps.user.driver.apps.DriverConfig',
    'apps.taxi.apps.TaxiConfig',
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
    'http://localhost:5175',    # Another alternative port
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
    'http://127.0.0.1:5175',
]

# Avoid silent POST redirects on API endpoints when slash is missing
APPEND_SLASH = False

STATIC_URL = '/static/'

POSTAL_CODE_API_URL = os.environ.get(
    'POSTAL_CODE_API_URL',
    'https://www.cttcodigopostal.pt/api/getzipcode',
)

JWT_SECRET = os.environ.get('JWT_SECRET', SECRET_KEY)
JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', 24))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bd',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': os.environ.get('DB_HOST', 'db'),  # 'db' é o nome do serviço Docker
        'PORT': '5432',
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',  # Apenas JSON
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}