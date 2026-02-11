class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = "change-this-secret-key"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
