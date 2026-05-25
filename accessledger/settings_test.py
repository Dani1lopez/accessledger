import os

from .settings import *
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env.test", override=True)

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-test-key-ci-only")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "accessledger",
        "USER": os.getenv("POSTGRES_USER", "danidev_dj"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AXES_ENABLED = False
