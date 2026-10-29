"""Environment-based configuration for local preview and MySQL deployment."""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or (not DEBUG and SECRET_KEY.startswith("local-development")):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY; production requires a random secret.")
ALLOWED_HOSTS = [s.strip() for s in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if s.strip()]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "shop",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
engine = os.getenv("DB_ENGINE", "sqlite")
if engine == "mysql":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.mysql", "NAME": os.environ["MYSQL_DATABASE"],
        "USER": os.environ["MYSQL_USER"], "PASSWORD": os.environ["MYSQL_PASSWORD"],
        "HOST": os.getenv("MYSQL_HOST", "127.0.0.1"), "PORT": os.getenv("MYSQL_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
    }}
elif engine == "sqlite":
    if not DEBUG:
        raise ImproperlyConfigured("SQLite is for local preview only; use MySQL in production.")
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "db.sqlite3"))}}
else:
    raise ImproperlyConfigured("DB_ENGINE must be sqlite or mysql.")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "catalog"
LOGOUT_REDIRECT_URL = "catalog"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# No platform credentials: explicitly opt in to a demonstration, never real money.
DEMO_PAYMENT_ENABLED = os.getenv("DEMO_PAYMENT_ENABLED", "true" if DEBUG else "false").lower() == "true"
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "orangible@example.invalid")
