import logging
import sys
import os

# Настраиваем путь для импорта пакета
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from figma_telegram_bot.bot.bot import run_bot
from figma_telegram_bot.config.settings import DEBUG_MODE

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG if DEBUG_MODE else logging.WARNING,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main():

    logger.info("Запуск Figma Telegram бота")
    try:
        run_bot()
    except Exception as e:
        logger.error(f"Произошла ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
