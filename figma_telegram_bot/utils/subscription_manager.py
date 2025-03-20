import json
import os
import logging
from typing import Dict, Set, List

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Менеджер подписок пользователей на файлы и комментарии Figma"""

    def __init__(self, storage_path: str = "user_subscriptions.json"):
        """
        Инициализация менеджера подписок

        Args:
            storage_path: Путь к файлу для хранения подписок
        """
        self.storage_path = storage_path

        # Словарь подписок на обновления файлов
        # {chat_id (str): [file_keys]}
        self.user_subscriptions: Dict[int, Set[str]] = {}

        # Словарь подписок на комментарии
        # {chat_id (str): [file_keys]}
        self.comment_subscriptions: Dict[int, Set[str]] = {}

        # Загружаем сохраненные подписки
        self._load_subscriptions()

        # Логируем информацию о загруженных подписках
        logger.info(f"Загружено {len(self.user_subscriptions)} подписок на файлы")
        logger.info(
            f"Загружено {len(self.comment_subscriptions)} подписок на комментарии"
        )

    def _load_subscriptions(self) -> None:
        """Загрузка сохраненных подписок из JSON-файла"""
        if not os.path.exists(self.storage_path):
            logger.info(f"Файл подписок {self.storage_path} не найден. Создаем новый.")
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Преобразуем данные из JSON в словари с множествами
                # chat_id из строки в число, и списки в множества
                self.user_subscriptions = {
                    int(k): set(v)
                    for k, v in data.get("user_subscriptions", {}).items()
                }

                self.comment_subscriptions = {
                    int(k): set(v)
                    for k, v in data.get("comment_subscriptions", {}).items()
                }

                logger.info(f"Подписки успешно загружены из {self.storage_path}")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при загрузке подписок: {e}")

    def _save_subscriptions(self) -> None:
        """Сохранение подписок в JSON-файл"""
        try:
            # Преобразуем множества в списки и chat_id в строки для JSON
            data = {
                "user_subscriptions": {
                    str(k): list(v) for k, v in self.user_subscriptions.items()
                },
                "comment_subscriptions": {
                    str(k): list(v) for k, v in self.comment_subscriptions.items()
                },
            }

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Подписки успешно сохранены в {self.storage_path}")
        except IOError as e:
            logger.error(f"Ошибка при сохранении подписок: {e}")

    def add_file_subscription(self, chat_id: int, file_key: str) -> None:
        """
        Добавление подписки пользователя на обновления файла

        Args:
            chat_id: ID чата пользователя
            file_key: Ключ файла Figma
        """
        if chat_id not in self.user_subscriptions:
            self.user_subscriptions[chat_id] = set()

        self.user_subscriptions[chat_id].add(file_key)
        self._save_subscriptions()
        logger.info(f"Добавлена подписка на файл {file_key} для пользователя {chat_id}")

    def remove_file_subscription(self, chat_id: int, file_key: str) -> bool:
        """
        Удаление подписки пользователя на обновления файла

        Args:
            chat_id: ID чата пользователя
            file_key: Ключ файла Figma

        Returns:
            True, если подписка была удалена, False - если подписки не было
        """
        if (
            chat_id not in self.user_subscriptions
            or file_key not in self.user_subscriptions[chat_id]
        ):
            return False

        self.user_subscriptions[chat_id].remove(file_key)

        # Если у пользователя не осталось подписок, удаляем запись
        if not self.user_subscriptions[chat_id]:
            del self.user_subscriptions[chat_id]

        self._save_subscriptions()
        logger.info(f"Удалена подписка на файл {file_key} для пользователя {chat_id}")
        return True

    def add_comment_subscription(self, chat_id: int, file_key: str) -> None:
        """
        Добавление подписки пользователя на комментарии файла

        Args:
            chat_id: ID чата пользователя
            file_key: Ключ файла Figma
        """
        if chat_id not in self.comment_subscriptions:
            self.comment_subscriptions[chat_id] = set()

        self.comment_subscriptions[chat_id].add(file_key)
        self._save_subscriptions()
        logger.info(
            f"Добавлена подписка на комментарии файла {file_key} для пользователя {chat_id}"
        )

    def remove_comment_subscription(self, chat_id: int, file_key: str) -> bool:
        """
        Удаление подписки пользователя на комментарии файла

        Args:
            chat_id: ID чата пользователя
            file_key: Ключ файла Figma

        Returns:
            True, если подписка была удалена, False - если подписки не было
        """
        if (
            chat_id not in self.comment_subscriptions
            or file_key not in self.comment_subscriptions[chat_id]
        ):
            return False

        self.comment_subscriptions[chat_id].remove(file_key)

        # Если у пользователя не осталось подписок на комментарии, удаляем запись
        if not self.comment_subscriptions[chat_id]:
            del self.comment_subscriptions[chat_id]

        self._save_subscriptions()
        logger.info(
            f"Удалена подписка на комментарии файла {file_key} для пользователя {chat_id}"
        )
        return True

    def get_file_subscribers(self, file_key: str) -> List[int]:
        """
        Получение списка пользователей, подписанных на обновления файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Список ID чатов подписчиков
        """
        subscribers = []
        for chat_id, file_keys in self.user_subscriptions.items():
            if file_key in file_keys:
                subscribers.append(chat_id)
        return subscribers

    def get_comment_subscribers(self, file_key: str) -> List[int]:
        """
        Получение списка пользователей, подписанных на комментарии файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Список ID чатов подписчиков
        """
        subscribers = []
        for chat_id, file_keys in self.comment_subscriptions.items():
            if file_key in file_keys:
                subscribers.append(chat_id)
        return subscribers

    def get_user_file_subscriptions(self, chat_id: int) -> Set[str]:
        """
        Получение списка файлов, на которые подписан пользователь

        Args:
            chat_id: ID чата пользователя

        Returns:
            Множество ключей файлов
        """
        return self.user_subscriptions.get(chat_id, set())

    def get_user_comment_subscriptions(self, chat_id: int) -> Set[str]:
        """
        Получение списка файлов, на комментарии которых подписан пользователь

        Args:
            chat_id: ID чата пользователя

        Returns:
            Множество ключей файлов
        """
        return self.comment_subscriptions.get(chat_id, set())

    def is_user_subscribed_to_file(self, chat_id: int, file_key: str) -> bool:
        """
        Проверка, подписан ли пользователь на обновления файла

        Args:
            chat_id: ID чата пользователя
            file_key: Ключ файла Figma

        Returns:
            True, если подписан, иначе False
        """
        return (
            chat_id in self.user_subscriptions
            and file_key in self.user_subscriptions[chat_id]
        )

    def is_user_subscribed_to_comments(self, chat_id: int, file_key: str) -> bool:
        """
        Проверка, подписан ли пользователь на комментарии файла

        Args:
            chat_id: ID чата пользователя
            file_key: Ключ файла Figma

        Returns:
            True, если подписан, иначе False
        """
        return (
            chat_id in self.comment_subscriptions
            and file_key in self.comment_subscriptions[chat_id]
        )

    def has_any_file_subscribers(self, file_key: str) -> bool:
        """
        Проверка, есть ли подписчики на обновления файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            True, если есть хотя бы один подписчик
        """
        return any(file_key in subs for subs in self.user_subscriptions.values())

    def has_any_comment_subscribers(self, file_key: str) -> bool:
        """
        Проверка, есть ли подписчики на комментарии файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            True, если есть хотя бы один подписчик
        """
        return any(file_key in subs for subs in self.comment_subscriptions.values())
