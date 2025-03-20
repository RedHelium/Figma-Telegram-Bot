import os
from dotenv import load_dotenv


load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

FIGMA_API_TOKEN = os.environ.get("FIGMA_API_TOKEN")
FIGMA_API_BASE_URL = os.environ.get("FIGMA_API_BASE_URL", "https://api.figma.com/v1")

DEBUG_MODE = os.environ.get("DEBUG_MODE", "False").lower() == "true"

CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))  # По умолчанию 5 минут

AUTO_SUBSCRIBE_COMMENTS = (
    os.environ.get("AUTO_SUBSCRIBE_COMMENTS", "True").lower() == "true"
)
