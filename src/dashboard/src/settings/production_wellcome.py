from __future__ import absolute_import

import dj_database_url

from .base import *


DATABASES['default'] = dj_database_url.config(env='ARCHIVEMATICA_DASHBOARD_DB_URL', conn_max_age=600)

STATIC_ROOT = os.environ.get(
    'DJANGO_STATIC_ROOT', os.path.join(BASE_PATH, 'static')
)

STATICFILES_DIRS = (
    ('js', os.path.join(STATIC_ROOT, 'media', 'js')),
    ('css', os.path.join(STATIC_ROOT, 'media', 'css')),
    ('images', os.path.join(STATIC_ROOT, 'media', 'images')),
    ('vendor', os.path.join(STATIC_ROOT, 'media', 'vendor')),
)

ALLOWED_HOSTS = ['*']

SECRET_KEY = '12345'
