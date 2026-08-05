from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

# Load local development environment variables from backend/.env.
# Vercel and other deployment platforms provide variables directly.
load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------------------
# Core Django configuration
# ---------------------------------------------------------------------

DEBUG = os.getenv("DJANGO_DEBUG", "true").strip().lower() == "true"

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "unsafe-local-development-key",
).strip()

# Prevent accidental production deployment with the development key.
if not DEBUG and SECRET_KEY == "unsafe-local-development-key":
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be configured when DJANGO_DEBUG is false."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,.vercel.app",
    ).split(",")
    if host.strip()
]

# Next.js frontend URL.
# Django Admin's â€œView siteâ€ link will use this value.
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:3000",
).strip().rstrip("/")


# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "incidents",
]


# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ---------------------------------------------------------------------
# URL, templates and application entry points
# ---------------------------------------------------------------------

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    # Production database, such as Neon PostgreSQL.
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=0,
            ssl_require=not DEBUG,
        )
    }
else:
    # Local development database.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ---------------------------------------------------------------------
# Authentication and password validation
# ---------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": (
        "rest_framework.pagination.PageNumberPagination"
    ),
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),
    "EXCEPTION_HANDLER": (
        "config.exceptions.api_exception_handler"
    ),
}


# ---------------------------------------------------------------------
# JWT authentication
# ---------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}


# ---------------------------------------------------------------------
# OpenAPI documentation
# ---------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "TriageIQ API",
    "DESCRIPTION": (
        "Django REST API for AI-assisted incident triage "
        "and resolution."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ---------------------------------------------------------------------
# Frontend access, CORS and CSRF
# ---------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

# The frontend uses JWT tokens through the Authorization header rather
# than cross-origin session cookies.
CORS_ALLOW_CREDENTIALS = False


# ---------------------------------------------------------------------
# AI configuration
# ---------------------------------------------------------------------

# Mock mode produces deterministic results and needs no API key.
AI_MODE = os.getenv("AI_MODE", "mock").strip().lower()

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "groq",
).strip()

AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    "https://api.groq.com/openai/v1",
).strip().rstrip("/")

AI_API_KEY = os.getenv(
    "AI_API_KEY",
    "",
).strip()

AI_MODEL = os.getenv(
    "AI_MODEL",
    "openai/gpt-oss-20b",
).strip()

AI_FALLBACK_MODEL = os.getenv(
    "AI_FALLBACK_MODEL",
    "openai/gpt-oss-120b",
).strip()

AI_TIMEOUT_SECONDS = int(
    os.getenv("AI_TIMEOUT_SECONDS", "45")
)


# ---------------------------------------------------------------------
# Report configuration
# ---------------------------------------------------------------------

REPORT_BRAND_NAME = "TriageIQ"
REPORT_ACCENT_HEX = "#B9855A"


# ---------------------------------------------------------------------
# Temporary incident-source uploads
# ---------------------------------------------------------------------

# R2 lifecycle rules perform physical expiry.
# The application also blocks access as soon as expires_at is reached.
TEMP_UPLOAD_STORAGE_MODE = os.getenv(
    "TEMP_UPLOAD_STORAGE_MODE",
    "local",
).strip().lower()

TEMP_UPLOAD_LOCAL_ROOT = os.getenv(
    "TEMP_UPLOAD_LOCAL_ROOT",
    str(BASE_DIR / ".temporary-uploads"),
).strip()

TEMP_UPLOAD_MAX_BYTES = (
    int(os.getenv("TEMP_UPLOAD_MAX_MB", "4"))
    * 1024
    * 1024
)

TEMP_UPLOAD_MAX_PDF_PAGES = int(
    os.getenv("TEMP_UPLOAD_MAX_PDF_PAGES", "25")
)

TEMP_UPLOAD_MAX_LOG_LINES = int(
    os.getenv("TEMP_UPLOAD_MAX_LOG_LINES", "5000")
)

TEMP_UPLOAD_MAX_EXTRACTED_CHARS = int(
    os.getenv("TEMP_UPLOAD_MAX_EXTRACTED_CHARS", "15000")
)

TEMP_UPLOAD_RETENTION_CHOICES = (7, 10)


# ---------------------------------------------------------------------
# Cloudflare R2
# ---------------------------------------------------------------------

R2_ENDPOINT_URL = os.getenv(
    "R2_ENDPOINT_URL",
    "",
).strip().rstrip("/")

R2_ACCESS_KEY_ID = os.getenv(
    "R2_ACCESS_KEY_ID",
    "",
).strip()

R2_SECRET_ACCESS_KEY = os.getenv(
    "R2_SECRET_ACCESS_KEY",
    "",
).strip()

R2_BUCKET_NAME = os.getenv(
    "R2_BUCKET_NAME",
    "",
).strip()


# ---------------------------------------------------------------------
# Production security
# ---------------------------------------------------------------------

if not DEBUG:
    # Vercel and similar platforms terminate HTTPS before forwarding
    # the request to Django.
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
