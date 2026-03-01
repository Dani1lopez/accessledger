from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "accessledger",
        "USER": "danidev_dj",
        "PASSWORD": "12345_dj",
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}