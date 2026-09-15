import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
from celery.schedules import crontab

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'channels',
    'channels_redis',
    'django_celery_beat',

    # Local apps
    'core.apps.CoreConfig',
    'users.apps.UsersConfig',
    'venues.apps.VenuesConfig',
    'staff.apps.StaffConfig',
    'tables.apps.TablesConfig',
    'guest_sessions.apps.GuestSessionsConfig',
    'orders.apps.OrdersConfig',
    'payments.apps.PaymentsConfig',
    'events.apps.EventsConfig',
    'explore.apps.ExploreConfig',
    'gate.apps.GateConfig',
    'notifications.apps.NotificationsConfig',
    'hq.apps.HqConfig',
    'control.apps.ControlConfig',
    'rbac',
    'security.apps.SecurityConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'security.middleware.SecurityMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'middleware.auth_middleware.AuthMiddleware',
    'middleware.redis_session_middleware.RedisSessionMiddleware',
    'middleware.zero_trust_proxy.ZeroTrustProxyMiddleware',
    'middleware.timezone_middleware.TimezoneMiddleware',
    'hq.middleware.RequestLogMiddleware',
]

ROOT_URLCONF = 'epearl.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'epearl.wsgi.application'
ASGI_APPLICATION = 'epearl.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'epearl_db'),
        'USER': os.getenv('DB_USER', 'epearl_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'your_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Redis Cache Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.getenv('REDIS_PASSWORD', ''),
        }
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

USER_SESSION_TIMEOUT = 60 * 60 * 8  # 8 hours
ADMIN_LOGIN_TOKEN_EXPIRY = 60 * 20  # 20 minutes

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# =============================================================================
# Django REST Framework Settings
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# =============================================================================
# JWT Settings (Simple JWT)
# =============================================================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',
}

# =============================================================================
# CORS Settings
# =============================================================================

CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

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

# =============================================================================
# Channels (WebSocket) Settings
# =============================================================================

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), 6379)],
        },
    },
}

# =============================================================================
# Celery Settings (Async Tasks)
# =============================================================================

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# =============================================================================
# Celery Beat Schedule (for scheduled tasks)
# =============================================================================

CELERY_BEAT_SCHEDULE = {
    # Existing tasks
    'send-shift-reminders': {
        'task': 'notifications.tasks.send_shift_reminders',
        'schedule': crontab(minute='*/15'),
    },
    'send-booking-reminders': {
        'task': 'notifications.tasks.send_booking_reminders',
        'schedule': crontab(minute='*/30'),
    },
    'send-subscription-expiry-reminders': {
        'task': 'notifications.tasks.send_subscription_expiry_reminders',
        'schedule': crontab(hour=0, minute=0),
    },
    'check-service-health': {
        'task': 'hq.tasks.check_service_health',
        'schedule': crontab(minute='*/5'),
    },
    'charge-subscriptions': {
        'task': 'hq.tasks.charge_subscriptions',
        'schedule': crontab(hour=0, minute=5),
    },
    # Security tasks
    'update-security-analytics': {
        'task': 'security.tasks.update_security_analytics',
        'schedule': crontab(minute='*/5'),
    },
    # NEW: Trial reminders (daily at 9am)
    'send-trial-reminders': {
        'task': 'notifications.tasks.send_trial_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
}

# =============================================================================
# Custom E-Pearl Settings
# =============================================================================

APP_NAME = os.getenv('APP_NAME', 'E-Pearl')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
ADMIN_IP_WHITELIST = os.getenv('ADMIN_IP_WHITELIST', '127.0.0.1').split(',')

# =============================================================================
# Email Settings (SMTP)
# =============================================================================

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@epearl.co.ke')

# =============================================================================
# SMS Settings (Africa's Talking)
# =============================================================================

AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME', '')
AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY', '')
AFRICASTALKING_SHORTCODE = os.getenv('AFRICASTALKING_SHORTCODE', '')
SMS_CREDITS_THRESHOLD = 100

# =============================================================================
# Payment Gateway Settings
# =============================================================================

MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '')
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '')
MPESA_ENVIRONMENT = os.getenv('MPESA_ENVIRONMENT', 'sandbox')
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', 'https://your-domain.com/api/payments/webhook/')

FLUTTERWAVE_PUBLIC_KEY = os.getenv('FLUTTERWAVE_PUBLIC_KEY', '')
FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY', '')
FLUTTERWAVE_ENCRYPTION_KEY = os.getenv('FLUTTERWAVE_ENCRYPTION_KEY', '')
FLUTTERWAVE_ENVIRONMENT = os.getenv('FLUTTERWAVE_ENVIRONMENT', 'sandbox')
FLUTTERWAVE_REDIRECT_URL = os.getenv('FLUTTERWAVE_REDIRECT_URL', 'https://your-domain.com/api/payments/flutterwave/callback/')

# =============================================================================
# Encryption Settings (for payment credentials)
# =============================================================================

FERNET_KEY = os.getenv('FERNET_KEY', '')

# =============================================================================
# Error Tracking
# =============================================================================

SENTRY_DSN = os.getenv('SENTRY_DSN', '')

# =============================================================================
# Business Settings
# =============================================================================

ADMIN_LOGIN_URL_EXPIRY = 20  # minutes

SUBSCRIPTION_TIERS = {
    'seed': {'price': 4500, 'label': 'Seed'},
    'spark': {'price': 8500, 'label': 'Spark'},
    'rose': {'price': 15000, 'label': 'Rose'},
    'summit': {'price': 20000, 'label': 'Summit'},
    'elite': {'price': 25000, 'label': 'Elite'},
    'legacy': {'price': 30000, 'label': 'Legacy'},
}

PLATFORM_FEE_PERCENTAGE = 2
EXIT_QR_EXPIRY = 2  # minutes

# =============================================================================
# Authentication Lockout Settings
# =============================================================================

LOCKOUT_MAX_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes
LOCKOUT_PASSWORD_EXPIRY_DAYS = 90
LOCKOUT_PIN_EXPIRY_DAYS = 365

# =============================================================================
# Billing & Subscription Settings
# =============================================================================

BILLING_GRACE_PERIOD_DAYS = 7
BILLING_RETRY_ATTEMPTS = 3

# =============================================================================
# NEW: Trial Period Setting
# =============================================================================

TRIAL_PERIOD_DAYS = 14

# =============================================================================
# Security Notification Settings
# =============================================================================

SECURITY_ADMIN_EMAILS = os.getenv('SECURITY_ADMIN_EMAILS', 'admin@epearl.co.ke').split(',')
SECURITY_ADMIN_PHONES = os.getenv('SECURITY_ADMIN_PHONES', '+2547XXXXXXXX').split(',')
SECURITY_NOTIFY_ALL_EVENTS = os.getenv('SECURITY_NOTIFY_ALL_EVENTS', 'True') == 'True'

# =============================================================================
# Logging Configuration
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'epearl.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}