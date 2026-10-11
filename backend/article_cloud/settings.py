import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


INSECURE_DEV_KEY = 'dev-only-insecure-key'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', INSECURE_DEV_KEY)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

if not DEBUG and SECRET_KEY == INSECURE_DEV_KEY:
    raise ImproperlyConfigured('Defina DJANGO_SECRET_KEY quando DJANGO_DEBUG for False.')

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if host.strip()]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'accounts',
    'articles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Origens do front autorizadas a chamar a API (separadas por vírgula).
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:8080,http://localhost:8080').split(',')
    if origin.strip()
]

ROOT_URLCONF = 'article_cloud.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'article_cloud.wsgi.application'


# Sem DB_HOST usa SQLite local; com DB_HOST usa o PostgreSQL do RDS.
if os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ['DB_NAME'],
            'USER': os.environ['DB_USER'],
            'PASSWORD': os.environ['DB_PASSWORD'],
            'HOST': os.environ['DB_HOST'],
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {'sslmode': os.environ.get('DB_SSLMODE', 'require')},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


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


LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'

# Credenciais de acesso AWS
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_SESSION_TOKEN = os.environ.get('AWS_SESSION_TOKEN', '') 

# Servicos AWS
AWS_STORAGE_BUCKET_NAME = os.environ.get(
    'S3_BUCKET',
    os.environ.get('AWS_STORAGE_BUCKET_NAME', 'article-cloud'),
)
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
AWS_DYNAMODB_TABLE_NAME = os.environ.get('AWS_DYNAMODB_TABLE_NAME', 'LogsArtigos')