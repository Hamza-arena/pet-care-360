import os

from dotenv import load_dotenv

load_dotenv()


def normalize_db_url(url: str | None) -> str | None:
    if url and url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.environ.get('DATABASE_URL', 'sqlite:///petcare360.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    ITEMS_PER_PAGE = 20

    # Rate Limiting Defaults
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_ENABLED = True

    # Security Cookies
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    @classmethod
    def init_app(cls, app):
        pass


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-secret-key-change-in-prod')
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.environ.get('DATABASE_URL', 'sqlite:///petcare360_dev.db'))


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    SECRET_KEY = 'test-secret-key-12345'
    SQLALCHEMY_DATABASE_URI = normalize_db_url(os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:'))
    WTF_CSRF_ENABLED = False
    ITEMS_PER_PAGE = 10
    RATELIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

    @classmethod
    def init_app(cls, app):
        super().init_app(app)
        secret = os.environ.get('SECRET_KEY')
        if not secret or secret.strip() == '' or 'dev' in secret.lower() or 'secret-key-change' in secret.lower():
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "The SECRET_KEY environment variable MUST be explicitly set to a secure, "
                "non-default value in Production. The application will not start."
            )
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise RuntimeError(
                "CRITICAL CONFIGURATION ERROR: "
                "DATABASE_URL environment variable is required in Production."
            )


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Alias for backward compatibility
Config = DevelopmentConfig

