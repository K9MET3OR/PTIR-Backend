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
    'apps.user.client.apps.ClientConfig',
    'apps.user.admin.apps.AdminConfig',
    'apps.taxi.apps.TaxiConfig',
    'apps.trip.apps.TripConfig',
    'apps.shift.apps.ShiftConfig',
    'apps.refuel.apps.RefuelConfig',
    'apps.invoice.apps.InvoiceConfig',
]

import os

ALLOWED_HOSTS = ['*']

DEBUG = True
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

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

# Stripe Configuration
import stripe
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
stripe.api_key = STRIPE_SECRET_KEY

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bd',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': os.environ.get('DB_HOST', 'localhost'),  # 'db' é o nome do serviço Docker
        'PORT': '5432',
    }
}

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',  # Apenas JSON
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}