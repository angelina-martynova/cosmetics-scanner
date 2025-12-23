"""
Конфігурація програми Cosmetics Scanner
"""

import os
from datetime import timedelta

class Config:
    """Базова конфігурація"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # База даних
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'postgresql://postgres:AdminPostgres123!@localhost:5432/cosmetics_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Зовнішні API
    COSING_API_KEY = os.environ.get('COSING_API_KEY', '')
    OPENFOODFACTS_ENABLED = True
    PUBCHEM_ENABLED = True
    
    # Налаштування кешу
    CACHE_TYPE = 'filesystem'
    CACHE_DIR = 'data_cache'
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 година
    
    # Налаштування зовнішніх джерел
    EXTERNAL_SOURCES = {
        'cosing': {
            'enabled': True,
            'base_url': 'https://ec.europa.eu/growth/tools-databases/cosing/',
            'rate_limit': 10,  # запитів на хвилину
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
        }
    }
    
    # Налаштування програми
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'txt', 'pdf'}
    
    # Налаштування безпеки
    SESSION_COOKIE_SECURE = False  # True для продакшена з HTTPS
    REMEMBER_COOKIE_DURATION = timedelta(days=30)


class DevelopmentConfig(Config):
    """Конфігурація для розробки"""
    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    """Конфігурація для продакшена"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Конфігурація для тестування"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Словник конфігурацій
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}