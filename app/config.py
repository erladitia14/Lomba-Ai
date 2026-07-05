import os

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def _load_env_file():
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_file()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "hazza-learnai-dev-key")
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))
    ALLOWED_EXTENSIONS = {"pdf"}

    PDF_MAX_PAGES = int(os.environ.get("PDF_MAX_PAGES", "24"))
    PDF_MAX_TEXT_CHARS = int(os.environ.get("PDF_MAX_TEXT_CHARS", "70000"))
    CLEAN_TEXT_MAX_CHARS = int(os.environ.get("CLEAN_TEXT_MAX_CHARS", "30000"))

    GEMINI_ENABLED = os.environ.get("GEMINI_ENABLED", "true").lower() == "true"
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_FALLBACK_ENABLED = os.environ.get("GEMINI_FALLBACK_ENABLED", "true").lower() == "true"
    GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "180"))
    GEMINI_MAX_INPUT_CHARS = int(os.environ.get("GEMINI_MAX_INPUT_CHARS", "9000"))
