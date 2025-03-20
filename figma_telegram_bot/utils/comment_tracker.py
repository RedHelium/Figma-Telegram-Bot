import logging
import json
import os
from typing import Dict, List, Tuple, Set

from figma_telegram_bot.figma_api.client import FigmaClient

logger = logging.getLogger(__name__)


class FigmaCommentTracker:
    """Отслеживание новых комментариев в файлах Figma"""

    def __init__(self, storage_path: str = "file_comments.json"):
        """
        Инициализация трекера комментариев

        Args:
            storage_path: Путь к файлу для хранения информации о комментариях
        """
        self.storage_path = storage_path
        self.figma_client = FigmaClient()
        self.comments = self._load_comments()

        # Логируем начальное состояние для отладки
        logger.debug(
            f"Инициализирован CommentTracker. Отслеживаемые файлы: {list(self.comments.keys())}"
        )
        for file_key, comments in self.comments.items():
            logger.debug(f"Файл {file_key}: {len(comments)} комментариев")

    def _load_comments(self) -> Dict[str, Set[str]]:
        """
        Загрузка сохраненных ID комментариев файлов

        Returns:
            Словарь {file_key: set(comment_ids)}
        """
        if not os.path.exists(self.storage_path):
            logger.info(f"Файл {self.storage_path} не существует. Создаю новый.")
            return {}

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                comments_data = json.load(f)
                # Преобразуем списки обратно в множества
                result = {k: set(v) for k, v in comments_data.items()}
                logger.info(f"Загружено {len(result)} файлов с комментариями")
                return result
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при чтении файла комментариев: {e}")
            return {}

    def _save_comments(self) -> None:
        """Сохранение комментариев файлов в хранилище"""
        try:
            # Преобразуем множества в списки для сериализации JSON
            comments_data = {k: list(v) for k, v in self.comments.items()}

            # Логируем для отладки
            for file_key, comments in comments_data.items():
                logger.debug(
                    f"Сохраняю для файла {file_key}: {len(comments)} комментариев"
                )

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(comments_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Сохранены данные о комментариях в {self.storage_path}")
        except IOError as e:
            logger.error(f"Ошибка при сохранении файла комментариев: {e}")

    def add_file_to_track(self, file_key: str) -> None:
        """
        Добавление файла для отслеживания комментариев

        Args:
            file_key: Ключ файла Figma
        """
        # Получаем текущие комментарии и сохраняем их ID
        current_comments = self.figma_client.get_file_comments(file_key)
        comment_ids = {
            comment.get("id") for comment in current_comments if comment.get("id")
        }

        # Логируем для отладки
        logger.info(
            f"Добавляю файл {file_key} для отслеживания. Найдено {len(current_comments)} комментариев"
        )

        # Если файл уже отслеживается, объединяем множества комментариев
        if file_key in self.comments:
            old_count = len(self.comments[file_key])
            self.comments[file_key].update(comment_ids)
            new_count = len(self.comments[file_key])
            logger.info(
                f"Файл {file_key} уже отслеживается. Обновлено с {old_count} до {new_count} комментариев"
            )
        else:
            self.comments[file_key] = comment_ids
            logger.info(
                f"Файл {file_key} добавлен для отслеживания с {len(comment_ids)} комментариями"
            )

        self._save_comments()

    def remove_file_from_track(self, file_key: str) -> None:
        """
        Удаление файла из отслеживания

        Args:
            file_key: Ключ файла Figma
        """
        if file_key in self.comments:
            del self.comments[file_key]
            self._save_comments()
            logger.info(f"Файл {file_key} удален из отслеживания комментариев")
        else:
            logger.warning(f"Попытка удалить файл {file_key}, который не отслеживается")

    def check_file_comments(self, file_key: str) -> Tuple[List[Dict], bool]:
        """
        Проверка новых комментариев файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Кортеж (список_новых_комментариев, есть_ли_новые_комментарии)
        """
        if file_key not in self.comments:
            logger.warning(f"Файл {file_key} не отслеживается для комментариев")
            return [], False

        # Получаем текущие комментарии
        current_comments = self.figma_client.get_file_comments(file_key)
        logger.info(
            f"Проверка комментариев файла {file_key}. Текущее количество: {len(current_comments)}"
        )

        # Проверяем, есть ли новые комментарии
        known_comment_ids = self.comments[file_key]
        new_comments = []

        for comment in current_comments:
            comment_id = comment.get("id")
            if comment_id and comment_id not in known_comment_ids:
                logger.info(
                    f"Обнаружен новый комментарий: {comment_id} в файле {file_key}"
                )
                new_comments.append(comment)
                known_comment_ids.add(comment_id)

        # Если есть новые комментарии, обновляем хранилище
        if new_comments:
            self.comments[file_key] = known_comment_ids
            self._save_comments()
            logger.info(
                f"Обнаружено {len(new_comments)} новых комментариев в файле {file_key}"
            )

            # Выводим подробную информацию о новых комментариях для отладки
            for comment in new_comments:
                comment_id = comment.get("id", "")
                comment_text = (
                    comment.get("message", "")[:50] + "..."
                    if len(comment.get("message", "")) > 50
                    else comment.get("message", "")
                )
                user = comment.get("user", {}).get("handle", "Неизвестный")
                logger.debug(
                    f"Новый комментарий {comment_id} от {user}: '{comment_text}'"
                )

            return new_comments, True

        logger.info(f"Новых комментариев в файле {file_key} не обнаружено")
        return [], False

    def check_all_comments(self) -> Dict[str, List[Dict]]:
        """
        Проверка новых комментариев всех отслеживаемых файлов

        Returns:
            Словарь {file_key: список_новых_комментариев}
        """
        new_comments_by_file = {}
        logger.info(f"Проверка комментариев для {len(self.comments)} файлов")

        for file_key in list(self.comments.keys()):
            new_comments, has_new = self.check_file_comments(file_key)

            if has_new:
                new_comments_by_file[file_key] = new_comments
                logger.info(
                    f"В файле {file_key} найдено {len(new_comments)} новых комментариев"
                )

        if new_comments_by_file:
            logger.info(
                f"Всего найдено новых комментариев в {len(new_comments_by_file)} файлах"
            )
        else:
            logger.info("Новых комментариев не обнаружено")

        return new_comments_by_file

    def reset_comments_for_file(self, file_key: str) -> bool:
        """
        Сбросить отслеживаемые комментарии для файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            True если успешно, False если файл не отслеживается
        """
        if file_key not in self.comments:
            logger.warning(
                f"Попытка сбросить комментарии для файла {file_key}, который не отслеживается"
            )
            return False

        # Очищаем список комментариев для файла
        self.comments[file_key] = set()
        self._save_comments()
        logger.info(f"Сброшены комментарии для файла {file_key}")

        return True
