import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

JAZZMIN_SETTINGS = {
    "site_title": os.getenv("JAZZMIN_TITLE"),
    "site_header": os.getenv("JAZZMIN_HEADER"),
    "site_brand": os.getenv("JAZZMIN_BRAND"),
    "language_chooser": True,
}
