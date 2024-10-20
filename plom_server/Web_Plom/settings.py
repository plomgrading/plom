# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan

"""Django settings for Plom project.

Originally generated by 'django-admin startproject' using Django 4.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from typing import Any


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
# Some basic type-checking - PLOM_DEBUG must either be the string "0" or "1"
# Any values like "True", "False", "false", etc will be treated as truthy strings, i.e. "1"
# If it isn't set - i.e. None, default to keeping debug mode on
debug_setting = os.environ.get("PLOM_DEBUG")
if debug_setting is None:
    DEBUG = True
elif debug_setting.isdigit() and int(debug_setting) == 0:
    DEBUG = False
else:
    DEBUG = True


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("PLOM_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("When PLOM_DEBUG is off, you must set PLOM_SECRET_KEY")
    SECRET_KEY = "django-insecure-2ujgq&p27afoi(#3%^98vj2(274ic+j2rxemflb#z3z9x6z=rn"

# Notes on ports:
#   - PLOM_PUBLIC_FACING_PORT: where nginx or whoever will be expecting connections typically HTTPS
#     TODO: we need to know this (for CSRF), probably can be omitted if its 443
#   - PLOM_CONTAINER_PORT: the localhost port that django binds to for HTTP, default 8000
env_port = os.environ.get("PLOM_PUBLIC_FACING_PORT")
_port = ""
if env_port:
    _port = f":{env_port}"

# TODO: it bothers me that we need to know this (for CSRF)
_scheme = os.environ.get("PLOM_PUBLIC_FACING_SCHEME", "https")

# Use PLOM_PUBLIC_FACING_PREFIX if you want to proxy your connection like
# this: `https://plom.example.com/<prefix>/...`
#
# Finally, PLOM_HOSTNAME should be the external-facing hostname to which
# clients connect.
env_hostname = os.environ.get("PLOM_HOSTNAME")
if env_hostname:
    ALLOWED_HOSTS = [env_hostname]
    CSRF_TRUSTED_ORIGINS = [f"{_scheme}://{env_hostname}{_port}"]
else:
    ALLOWED_HOSTS = [".localhost", "127.0.0.1", "[::1]", "0.0.0.0"]
    CSRF_TRUSTED_ORIGINS = [f"{_scheme}://localhost{_port}"]

# I think these are supposed to help with generated URLs (such as initial login links)
# working.  It didn't seem to help for me.  Issue #3246 tracks this.
# USE_X_FORWARDED_HOST = True
# USE_X_FORWARDED_PORT = True
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Application definition

INSTALLED_APPS = [
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # for more sophisticated mathematics in templates (eg progressbars)
    "mathfilters",
    # for 'fun' with migrations - see #77
    "reset_migrations",
    # Huey + polymorphism
    "django_huey",
    "polymorphic",
    # HTMX
    "django_htmx",
    # REST framework
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    # Tables
    "django_tables2",
    # Custom apps
    "Launcher",
    "Base",
    "Authentication",
    "UserManagement",
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
    "Contrib",
    "TaskOrder",
    "Rectangles",
    "QuestionTags",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "Web_Plom.middleware.OnlineNowMiddleware",
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
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
                # add our own context processors
                "Web_Plom.context_processors.user_group_information",
                "Web_Plom.context_processors.plom_information",
            ],
        },
    },
]

WSGI_APPLICATION = "Web_Plom.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

plom_database_name = os.environ.get("PLOM_DATABASE_NAME") or "plom_db"

DATABASES = {
    "postgres": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": plom_database_name,
        "USER": os.environ.get("PLOM_DATABASE_USER") or "postgres",
        "PASSWORD": os.environ.get("PLOM_DATABASE_PASSWORD") or "postgres",
        "HOST": os.environ.get("PLOM_DATABASE_HOSTNAME") or "127.0.0.1",
        "PORT": os.environ.get("PLOM_DATABASE_PORT") or "5432",
    },
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        # TODO: note semantic difference: here the filename, above just the name
        "NAME": BASE_DIR / f"{plom_database_name}.sqlite3",
    },
}
# Users can choose a database backend via env var
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
# Default is 3 days, here we use 7 days
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 7


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
# Note: "collectstatic" command line copies files to this dir
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# Note: do not put inside the MEDIA_ROOT because the static files are versioned (Issue #3575)


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
            "filename": BASE_DIR / "huey/hueydb.sqlite3",
            "results": True,
            "store_none": False,
            "immediate": False,
            "utc": True,
            "consumer": {
                "workers": 4,
                "worker_type": "process",
                "initial_delay": 0.1,
                "backoff": 1.15,
                "max_delay": 10.0,
                "scheduler_interval": 60,
                "periodic": False,
                "check_worker_health": True,
                "health_check_interval": 300,
            },
        },
        "parentchores": {
            "huey_class": "huey.SqliteHuey",
            "filename": BASE_DIR / "huey/hueydb-parentchores.sqlite3",
            "results": True,
            "store_none": False,
            "immediate": False,
            "utc": True,
            "consumer": {
                "workers": 2,
                "worker_type": "process",
                "initial_delay": 0.1,
                "backoff": 1.15,
                "max_delay": 10.0,
                "scheduler_interval": 60,
                "periodic": False,
                "check_worker_health": True,
                "health_check_interval": 300,
            },
        },
    },
}

# DRF authentication and permissions
# The default permission must be set, otherwise it's AllowAny!
# see https://gitlab.com/plom/plom/-/issues/2904
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Media and user-uploaded files
# If you specify your own it should be fully qualified
_ = os.environ.get("PLOM_MEDIA_ROOT")
if _:
    MEDIA_ROOT = Path(_)
else:
    MEDIA_ROOT = BASE_DIR / "media"

# List of test fixture directories
FIXTURE_DIRS = [BASE_DIR / "fixtures"]

# Configurable variables for Web Plom
# ----------------------------------------------

# Max file size for bundle uploads in bytes (currently 512MiB), and other restrictions
# Note if Nginx or another tool is proxying, its limit will apply too.
# Most likely the proxy server's limit should be used for security.
MAX_BUNDLE_SIZE = 536870912
MAX_BUNDLE_PAGES = 2500

# Max file size for a single file upload (1 MB for now)
# MAX_FILE_SIZE = 1e6
# TODO: this is (probably) UNUSED at the moment, possible for future use.

LOGGING: dict[str, Any] = {
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

# When hunting down slow http request / db queries make use of the django-silk package
# https://github.com/jazzband/django-silk
PROFILER_SILK_ENABLED = True
if PROFILER_SILK_ENABLED:
    MIDDLEWARE.append("silk.middleware.SilkyMiddleware")
    INSTALLED_APPS.append("silk")

# When hunting down n-plus-1 query problems make use of the nplusone package
# https://github.com/jmcarp/nplusone
PROFILER_NPLUSONE_ENABLED = False
if PROFILER_NPLUSONE_ENABLED:
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

# django-tables2 configs
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"

DJANGO_TABLES2_TABLE_ATTRS = {
    "class": "table table-striped table-bordered",
    "thead": {
        "class": "table-light",
    },
}
