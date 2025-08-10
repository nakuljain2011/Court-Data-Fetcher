import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///data/database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    COURT_BASE_URL = os.environ.get('COURT_BASE_URL') or 'https://delhihighcourt.nic.in'
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
