"""
Конфігурація програми Cosmetics Scanner.

Вибір конфігурації — через змінну оточення APP_ENV
(development | production | testing). Див. .env.example.
"""

import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """Базова конфігурація (спільні значення)."""

    # ── Секрети / БД ──
    # Жодних дефолтних секретів у коді. Для локальної розробки значення
    # підставляє DevelopmentConfig; production вимагає env (див. init_app).
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Дефолт — локальний SQLite без будь-яких кредів. Реальна БД задається
    # лише через змінну оточення DATABASE_URL.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(BASE_DIR, 'cosmetics_dev.db'),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Запуск ──
    DEBUG = False
    PORT = int(os.environ.get('PORT', '5001'))

    # ── Зовнішні API ──
    COSING_API_KEY = os.environ.get('COSING_API_KEY', '')
    OPENFOODFACTS_ENABLED = True
    PUBCHEM_ENABLED = True

    # ── Кеш ──
    CACHE_TYPE = 'filesystem'
    CACHE_DIR = 'data_cache'
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 година

    EXTERNAL_SOURCES = {
        'cosing': {
            'enabled': True,
            'base_url': 'https://ec.europa.eu/growth/tools-databases/cosing/',
            'rate_limit': 10,
        },
        'openfoodfacts': {
            'enabled': True,
            'base_url': 'https://world.openfoodfacts.org/',
            'rate_limit': 30,
        },
        'pubchem': {
            'enabled': True,
            'base_url': 'https://pubchem.ncbi.nlm.nih.gov/',
            'rate_limit': 5,
        },
    }

    # ── Застосунок ──
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'txt', 'pdf'}

    # ── Безпека сесій ──
    SESSION_COOKIE_SECURE = False  # перевизначається у ProductionConfig
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=30)

    # ── Rate limiting (Flask-Limiter) ──
    # storage_uri: "memory://" достатньо для одного воркера; для кількох
    # воркерів/інстансів вкажіть redis://... через RATELIMIT_STORAGE_URI.
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    # Значення лімітів — рядки формату Flask-Limiter ("20 per day" тощо).
    SCAN_DAILY_LIMIT = os.environ.get('SCAN_DAILY_LIMIT', '20 per day')
    AUTH_RATE_LIMIT = os.environ.get('AUTH_RATE_LIMIT', '5 per minute')
    EXTERNAL_SEARCH_LIMIT = os.environ.get('EXTERNAL_SEARCH_LIMIT', '10 per minute')

    @staticmethod
    def init_app(app):
        """Хук ініціалізації. За замовчуванням нічого не робить."""
        return None


class DevelopmentConfig(Config):
    """Локальна розробка. Секрет підставляється, щоб не тримати .env обов'язковим."""
    DEBUG = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-insecure-key-change-me'


class ProductionConfig(Config):
    """Продакшн. Обов'язкові секрети приходять ТІЛЬКИ з оточення."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    @staticmethod
    def init_app(app):
        missing = [name for name in ('SECRET_KEY', 'DATABASE_URL')
                   if not os.environ.get(name)]
        if missing:
            raise RuntimeError(
                "APP_ENV=production, але не задані обов'язкові змінні оточення: "
                + ", ".join(missing)
                + ". Задайте їх перед запуском (див. .env.example)."
            )


class TestingConfig(Config):
    """Конфігурація для автотестів."""
    DEBUG = False
    TESTING = True
    SECRET_KEY = 'testing-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    RATELIMIT_STORAGE_URI = 'memory://'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
