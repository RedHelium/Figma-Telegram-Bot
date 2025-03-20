import logging
import requests
from typing import Dict, Any, List

from figma_telegram_bot.config.settings import FIGMA_API_TOKEN, FIGMA_API_BASE_URL

logger = logging.getLogger(__name__)


class FigmaClient:
    """Клиент для работы с Figma API"""

    def __init__(self, api_token: str = None, base_url: str = None):
        """
        Инициализация клиента Figma API

        Args:
            api_token: Персональный токен доступа к Figma API
            base_url: Базовый URL для Figma API
        """
        self.api_token = api_token or FIGMA_API_TOKEN
        self.base_url = base_url or FIGMA_API_BASE_URL
        self.headers = {
            "X-Figma-Token": self.api_token,
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict[str, Any]:
        """
        Выполнение запроса к Figma API

        Args:
            method: HTTP метод (GET, POST и т.д.)
            endpoint: Конечная точка API
            params: Параметры запроса (для GET)
            data: Данные запроса (для POST)

        Returns:
            Ответ от API в формате словаря
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.request(
                method=method, url=url, headers=self.headers, params=params, json=data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к Figma API: {e}")
            return {"error": str(e)}

    def get_file(self, file_key: str) -> Dict[str, Any]:
        """
        Получение информации о файле по его ключу

        Args:
            file_key: Ключ файла Figma (из URL)

        Returns:
            Словарь с информацией о файле
        """
        return self._make_request("GET", f"files/{file_key}")

    def get_file_version(self, file_key: str) -> str:
        """
        Получение текущей версии файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Версия файла или пустая строка в случае ошибки
        """
        try:
            file_info = self.get_file(file_key)
            return file_info.get("version", "")
        except Exception as e:
            logger.error(f"Ошибка при получении версии файла: {e}")
            return ""

    def get_file_versions(self, file_key: str) -> List[Dict[str, Any]]:
        """
        Получение истории версий файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Список версий файла
        """
        return self._make_request("GET", f"files/{file_key}/versions").get(
            "versions", []
        )

    def get_file_comments(self, file_key: str) -> List[Dict[str, Any]]:
        """
        Получение всех комментариев файла

        Args:
            file_key: Ключ файла Figma

        Returns:
            Список комментариев файла
        """
        result = self._make_request("GET", f"files/{file_key}/comments")
        return result.get("comments", [])

    def get_comment_details(self, file_key: str, comment_id: str) -> Dict[str, Any]:
        """
        Получение детальной информации о комментарии

        Args:
            file_key: Ключ файла Figma
            comment_id: ID комментария

        Returns:
            Словарь с информацией о комментарии
        """
        comments = self.get_file_comments(file_key)
        for comment in comments:
            if comment.get("id") == comment_id:
                return comment
        return {}

    def post_comment(
        self, file_key: str, message: str, client_meta: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Создание нового комментария в файле

        Args:
            file_key: Ключ файла Figma
            message: Текст комментария
            client_meta: Метаданные клиента (позиция комментария и т.д.)

        Returns:
            Созданный комментарий
        """
        data = {"message": message}

        if client_meta:
            data["client_meta"] = client_meta

        return self._make_request("POST", f"files/{file_key}/comments", data=data)

    def delete_comment(self, file_key: str, comment_id: str) -> Dict[str, Any]:
        """
        Удаление комментария

        Args:
            file_key: Ключ файла Figma
            comment_id: ID комментария

        Returns:
            Результат операции
        """
        return self._make_request("DELETE", f"files/{file_key}/comments/{comment_id}")
