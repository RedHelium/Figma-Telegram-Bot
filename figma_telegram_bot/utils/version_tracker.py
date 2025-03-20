import logging
import json
import os
from typing import Dict, Optional, List, Tuple

from figma_telegram_bot.figma_api.client import FigmaClient

logger = logging.getLogger(__name__)


class FigmaVersionTracker:
    """Отслеживание изменений версий файлов Figma"""

    def __init__(self, storage_path: str = "file_versions.json"):
        """
        Инициализация трекера версий

        Args:
            storage_path: Путь к файлу для хранения информации о версиях
        """
        self.storage_path = storage_path
        self.figma_client = FigmaClient()
        self.versions = self._load_versions()

    def _load_versions(self) -> Dict[str, str]:
        """
        Загрузка сохраненных версий файлов

        Returns:
            Словарь с версиями файлов {file_key: version}
        """
        if not os.path.exists(self.storage_path):
            return {}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при чтении файла версий: {e}")
            return {}

    def _save_versions(self) -> None:
        """Сохранение версий файлов в хранилище"""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.versions, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"Ошибка при сохранении файла версий: {e}")

    def add_file_to_track(self, file_key: str) -> None:
        """
        Добавление файла для отслеживания

        Args:
            file_key: Ключ файла Figma
        """
        if file_key in self.versions:
            return

        version = self.figma_client.get_file_version(file_key)
        if version:
            self.versions[file_key] = version
            self._save_versions()
            logger.info(
                f"Файл {file_key} добавлен для отслеживания с версией {version}"
            )

    def remove_file_from_track(self, file_key: str) -> None:
        """
        Удаление файла из отслеживания

        Args:
            file_key: Ключ файла Figma
        """
        if file_key in self.versions:
            del self.versions[file_key]
            self._save_versions()
            logger.info(f"Файл {file_key} удален из отслеживания")

    def check_file_updates(
        self, file_key: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Проверка обновлений файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Кортеж (изменился_ли_файл, старая_версия, новая_версия)
        """
        if file_key not in self.versions:
            logger.warning(f"Файл {file_key} не отслеживается")
            return False, None, None

        old_version = self.versions[file_key]
        new_version = self.figma_client.get_file_version(file_key)

        if not new_version:
            logger.error(f"Не удалось получить версию файла {file_key}")
            return False, old_version, None

        # Проверяем, изменилась ли версия
        if old_version != new_version:
            # Обновляем версию в хранилище
            self.versions[file_key] = new_version
            self._save_versions()
            logger.info(
                f"Обнаружено обновление файла {file_key}: {old_version} -> {new_version}"
            )
            return True, old_version, new_version

        return False, old_version, new_version

    def check_all_updates(self) -> List[Dict]:
        """
        Проверка обновлений всех отслеживаемых файлов

        Returns:
            Список словарей с информацией об изменившихся файлах
        """
        updated_files = []

        for file_key in list(self.versions.keys()):
            updated, old_version, new_version = self.check_file_updates(file_key)

            if updated:
                updated_files.append(
                    {
                        "file_key": file_key,
                        "old_version": old_version,
                        "new_version": new_version,
                    }
                )

        return updated_files
