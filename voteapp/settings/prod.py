import os

import dj_database_url

from .common import *

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-default-change-me-in-production"
)

# Defaulting split strings to empty lists or local defaults to avoid crashes
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost 127.0.0.1").split(" ")

DJANGO_SETTINGS_MODULE = os.environ.get(
    "DJANGO_SETTINGS_MODULE", "voteapp.settings.prod"
)

# --- DATABASE ---
# Falls back to an in-memory SQLite database if no URL is provided
DEFAULT_DB_URL =   'postgresql://postgres:postgres@votedbpro:5432/postgres'
DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
    )
}
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'

# --- SECURITY & COOKIES ---
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# Add the exact local address and port where your frontend UI runs
CORS_ALLOWED_ORIGINS = [
    "https://voteapp-mu.vercel.app",
    "http://localhost:3000", 
    "http://127.0.0.1:3000",
]

# Ensure Django's CSRF trusted origins match as well
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
]

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8000 http://127.0.0.1:8000"
).split(" ")

CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://voter:6379")

# Fall back to your local setup if REDIS_URL isn't set in environment variables
REDIS_URL = os.environ.get("REDIS_URL", "redis://voter:6379")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}
