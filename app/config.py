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
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"pdf"}

    NINE_ROUTER_ENABLED = os.environ.get("NINE_ROUTER_ENABLED", "true").lower() == "true"
    NINE_ROUTER_BASE_URL = os.environ.get("NINE_ROUTER_BASE_URL", "http://127.0.0.1:20128/api/v1")
    NINE_ROUTER_MODEL = os.environ.get("NINE_ROUTER_MODEL", "gh/gpt-4o-mini")
    NINE_ROUTER_API_KEY = os.environ.get("NINE_ROUTER_API_KEY", "")
    NINE_ROUTER_FALLBACK_ENABLED = os.environ.get("NINE_ROUTER_FALLBACK_ENABLED", "false").lower() == "true"
    NINE_ROUTER_TIMEOUT = int(os.environ.get("NINE_ROUTER_TIMEOUT", "120"))
    NINE_ROUTER_MAX_INPUT_CHARS = int(os.environ.get("NINE_ROUTER_MAX_INPUT_CHARS", "14000"))
