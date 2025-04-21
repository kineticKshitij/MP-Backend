"""
Django settings for Backend project using JWT authentication.
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config  # Use python-decouple for environment management

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "minorproject347d@gmail.com"  # Replace with your email
EMAIL_HOST_PASSWORD = "yanzzyizaomyuswn"  # Use App Password or SMTP password
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# Start the Django development server

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='your-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['localhost', '127.0.0.1','*','192.168.139.129']

# Application definition
INSTALLED_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',  # JWT authentication
    'corsheaders',               # Handle CORS for React frontend
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Home.apps.HomeConfig',
    'bootstrap4',  # Changed from django_bootstrap4 to bootstrap4
]

# Add Bootstrap4 settings
BOOTSTRAP4 = {
    'include_jquery': True,
}

# Debug Toolbar settings
INTERNAL_IPS = [
    '127.0.0.1',
]

# Debug Toolbar Configuration
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
}

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',  # Must be first
    'corsheaders.middleware.CorsMiddleware',  # Must be high in the order
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection as needed
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "Templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Backend.wsgi.application'

# Database configuration (MongoDB for development)
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'minor_project_db',
        'ENFORCE_SCHEMA': True,
        'CLIENT': {
            'host': 'mongodb://localhost:27017/',
            'username': '',
            'password': '',
            'authSource': 'admin',
        },
        'OPTIONS': {
            'operations_class': 'Backend.db_operations.CustomDatabaseOperations',
            'connect': True,
        }
    }
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Handles Organization authentication
    'Home.backends.EmployeeSignupBackend',          # Handles EmployeeSignup authentication
]

# Set the primary user model.
# Since Django supports only one custom user model per project,
# this is set to "Home.Organization". You must choose one primary model.
AUTH_USER_MODEL = "Home.Organization"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework: Use JWT Authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# Simple JWT configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=300),  # Adjust token lifetime as needed
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS configuration: allow your React frontend to access the backend
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://192.168.139.161",
]
CORS_ALLOW_CREDENTIALS = True

# Session and CSRF cookie settings (for non-JWT parts, if needed)
SESSION_COOKIE_SECURE = False  # Use True in production with HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = False

# Django Debug Toolbar (optional, only in development)
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]