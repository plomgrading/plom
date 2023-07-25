# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna

"""
Django settings for Web_Plom project.

Generated by 'django-admin startproject' using Django 4.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""
import logging
import os
from pathlib import Path

# Yuck, replace this below when we drop Python 3.8 support
from typing import Dict, Any


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-2ujgq&p27afoi(#3%^98vj2(274ic+j2rxemflb#z3z9x6z=rn"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [".localhost", "127.0.0.1", "[::1]", "0.0.0.0"]


# Application definition

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # for 'fun' with migrations - see #77
    "reset_migrations",
    # Huey + polymorphism
    "django_huey",
    "polymorphic",
    # REST framework
    "rest_framework",
    "rest_framework.authtoken",
    # add newly created app folder below
    "Base",
    "Authentication",
    "Preparation",
    "Papers",
    "SpecCreator",
    "Profile",
    "BuildPaperPDF",
    "Scan",
    "API",
    "Mark",
    "Identify",
    "Progress",
    "Rubrics",
    "Demo",
    "Finish",
    "Tags",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "Web_Plom.middleware.OnlineNowMiddleware",
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
]

ROOT_URLCONF = "Web_Plom.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Web_Plom.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

# set postgres hostname to "postgres" if running on docker
in_docker = os.environ.get("PLOM_USING_DOCKER")
if in_docker:
    postgres_hostname = "postgres"
else:
    postgres_hostname = "127.0.0.1"

DATABASES = {
    "postgres": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "plom_db",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": postgres_hostname,
        "PORT": "5432",
    },
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}
# Issue #2619: users can choose a database backend via env var
default = os.environ.get("PLOM_DATABASE_BACKEND")
if not default:
    default = "postgres"
DATABASES["default"] = DATABASES[default]

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Password reset timeout in seconds
# Default is 3 days
# PASSWORD_RESET_TIMEOUT = 60


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "static/"

STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# If the user is logged in and there is no activity for 2 hours, the login status will expire
SESSION_COOKIE_AGE = 60 * 60 * 2
# Every time user makes request, the session cookie age will be rescheduled to 2 hours
SESSION_SAVE_EVERY_REQUEST = True


# Django huey configuration
HUEY = {"immediate": False}
DJANGO_HUEY = {
    "default": "tasks",
    "queues": {
        "tasks": {
            "huey_class": "huey.SqliteHuey",
            "filename": "huey/huey_db.sqlite3",
            "results": True,
            "store_none": False,
            "immediate": False,
            "utc": True,
            "consumer": {
                "workers": 8,
                "worker_type": "process",
                "initial_delay": 0.1,
                "backoff": 1.15,
                "max_delay": 10.0,
                "scheduler_interval": 60,
                "periodic": False,
                "check_worker_health": True,
                "health_check_interval": 300,
            },
        }
    },
}

# DRF authentication
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
}

# Media and user-uploaded files
MEDIA_ROOT = BASE_DIR / "media"

# Test fixtures directory
FIXTURE_DIRS = [BASE_DIR / "fixtures"]

# Configurable variables for Web Plom
# ----------------------------------------------

# Max file size for bundle uploads (1 GB for now)
MAX_BUNDLE_SIZE = 1e9

# Max file size for a single file upload (1 MB for now)
# MAX_FILE_SIZE = 1e6

LOGGING: Dict[str, Any] = {
    "version": 1,
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "propagate": True,
            "level": "DEBUG",
        }
    },
}

# When hunting down n-plus-1 query problems make use of the nplusone package
# https://github.com/jmcarp/nplusone

hunting_n_plus_one = False

if hunting_n_plus_one:
    INSTALLED_APPS.append("nplusone.ext.django")
    MIDDLEWARE.append("nplusone.ext.django.NPlusOneMiddleware")
    LOGGING["loggers"].update(
        {
            "nplusone": {
                "handlers": ["console"],
                "level": "WARN",
            }
        }
    )
    NPLUSONE_LOGGER = logging.getLogger("nplusone")
    NPLUSONE_LOG_LEVEL = logging.WARN
