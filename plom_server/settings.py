# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2024 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Philip D. Loewen

"""Django settings for Plom project."""

import logging
import os
from pathlib import Path
from typing import Any


# Paths inside the source code can use BASE_DIR / 'subdir'
# but we should assume this is READ-ONLY
BASE_DIR = Path(__file__).resolve().parent


# Since BASE_DIR refers to the source code, you can define a single
# directory where all the state will go.  The default is the current
# working directory.  In many cases, other variables can override this
# choice (e.g., PLOM_MEDIA_ROOT) but this allows single place for all
# non-database "state"
_ = os.environ.get("PLOM_BASE_DIR")
if not _:
    PLOM_BASE_DIR = Path(".")
else:
    PLOM_BASE_DIR = Path(_)


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
#   - the localhost port that django binds to for HTTP, defaults 8000 but can be changed on the command line
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
    "plom_server.Launcher",
    "plom_server.Base",
    "plom_server.Authentication",
    "plom_server.UserManagement",
    "plom_server.Preparation",
    "plom_server.Papers",
    "plom_server.SpecCreator",
    "plom_server.Profile",
    "plom_server.BuildPaperPDF",
    "plom_server.Scan",
    "plom_server.API",
    "plom_server.Mark",
    "plom_server.Identify",
    "plom_server.Progress",
    "plom_server.Rubrics",
    "plom_server.TestingSupport",
    "plom_server.Finish",
    "plom_server.Contrib",
    "plom_server.TaskOrder",
    "plom_server.Rectangles",
    "plom_server.QuestionTags",
    "plom_server.QuestionClustering",
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
    "plom_server.middleware.OnlineNowMiddleware",
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "plom_server.urls"

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
                "plom_server.context_processors.user_group_information",
                "plom_server.context_processors.plom_information",
            ],
        },
    },
]

WSGI_APPLICATION = "plom_server.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

plom_database_name = os.environ.get("PLOM_DATABASE_NAME") or "plom_db"

DATABASES = {
    "postgres": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": plom_database_name,
        "USER": os.environ.get("PLOM_DATABASE_USER") or "postgres",
        "PASSWORD": os.environ.get("PLOM_DATABASE_PASSWORD") or "postgres",
        "HOST": os.environ.get("PLOM_DATABASE_HOSTNAME") or "127.0.0.1",
        "PORT": os.environ.get("PLOM_DATABASE_PORT") or "5432",
    },
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        # TODO: note semantic difference: here the filename, above just the name
        "NAME": PLOM_BASE_DIR / f"{plom_database_name}.sqlite3",
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


# Password reset timeout in seconds. We suggest 14 days. If unspecified then system will use 3 days.
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 14


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# --------------------------------------
#
# Something important, see docs
STATIC_URL = "static/"
# These are the "source" dirs for static files.  The first one might be readonly (Issue #2932)
# Second one is a hack to get some oxymoronic "dynamic" static stuff: see extra pages, scrap
# pages, javascript downloads, etc).
STATICFILES_DIRS = [BASE_DIR / "static", "plom_extra_static"]
# Note: "collectstatic" command line copies files to this dir
STATIC_ROOT = PLOM_BASE_DIR / "staticfiles"
# Note: do not put inside the MEDIA_ROOT because the static files are versioned (Issue #3575)


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Web login sessions expire this many seconds after initial login (defaults: two weeks)
# SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 hours
# If True, then every time user makes a request, the timeout will be reset (some performance cost)
# SESSION_SAVE_EVERY_REQUEST = False
# You can set the cookie to expire when they close their browser (for some browsers anyway)
# SESSION_EXPIRE_AT_BROWSER_CLOSE = False


# Independent sessions when multiple servers on the same host
if os.environ.get("PLOM_PUBLIC_FACING_PORT"):
    SESSION_COOKIE_NAME = "sessionid" + os.environ.get("PLOM_PUBLIC_FACING_PORT")


# Media and user-uploaded files
# If you specify your own it should be fully qualified
_ = os.environ.get("PLOM_MEDIA_ROOT")
if not _:
    MEDIA_ROOT = PLOM_BASE_DIR / "media"
else:
    MEDIA_ROOT = Path(_)


# Django Huey configuration
# Huey handles background tasks/processes which we call "chores".
# PLOM_HUEY_PARENT_WORKERS controls how many simultaneous bundle processing
# chores can happen (additional bundles will queue).
# PLOM_HUEY_WORKERS are lower-level jobs such as extracting several pages from
# a bundle and reading the QR codes.
_huey_workers = int(os.environ.get("PLOM_HUEY_WORKERS", 4))
_huey_parent_workers = int(os.environ.get("PLOM_HUEY_PARENT_WORKERS", 2))
HUEY = {"immediate": False}
DJANGO_HUEY = {
    "default": "chores",
    "queues": {
        "chores": {
            "huey_class": "huey.SqliteHuey",
            "filename": PLOM_BASE_DIR / "hueydb.sqlite3",
            "results": True,
            "store_none": False,
            "immediate": False,
            "utc": True,
            "consumer": {
                "workers": _huey_workers,
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
            "filename": PLOM_BASE_DIR / "hueydb-parentchores.sqlite3",
            "results": True,
            "store_none": False,
            "immediate": False,
            "utc": True,
            "consumer": {
                "workers": _huey_parent_workers,
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


# List of test fixture directories
FIXTURE_DIRS = [BASE_DIR / "fixtures"]


# Configurable variables for Plom
# -------------------------------

# Max file size for bundle uploads in bytes (currently 512MiB), and other restrictions
# Note if Nginx or another tool is proxying, its limit will apply too.
# Most likely the proxy server's limit should be used for security.
MAX_BUNDLE_SIZE = 536870912
MAX_BUNDLE_PAGES = 2500

# User uploaded (non-bundle) files are rejected if they exceed this byte size.
# TODO: nginx also checks file size, does this serve a purpose?
MAX_FILE_SIZE = 1024 * 1024
MAX_FILE_SIZE_DISPLAY = "1 MiB"
# User uploaded files are written to /tmp if they exceed this, default is 2.5e6.
# FILE_UPLOAD_MAX_MEMORY_SIZE = 2.5e6

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

# For general debugging and introspection, consider the django-extensions app.
# Get it with "pip install django-extensions". One good tool this enables is
# the command "manage.py show_urls", which walks the tree of URL specifications
# and prints a complete list of all API URL's, with destinations and codenames.
# (For this one the server does not even need to be running.)
# See  https://github.com/django-extensions/django-extensions
USE_DJANGO_EXTENSIONS = False
if USE_DJANGO_EXTENSIONS:
    INSTALLED_APPS.append("django_extensions")

# When hunting down slow http request / db queries make use of the django-silk package
# https://github.com/jazzband/django-silk
PROFILER_SILK_ENABLED = False
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
