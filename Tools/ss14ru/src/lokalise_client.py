"""
Клиент для интеграции с Lokalise API
"""

from typing import List, Dict, Optional
from pathlib import Path
import requests
import logging
from collections import defaultdict

from .models import TranslationKey


class LokaliseClient:
    """Клиент для работы с Lokalise API"""

    def __init__(self, api_token: str, project_id: str):
        """
        Инициализация клиента

        Args:
            api_token: API токен Lokalise
            project_id: ID проекта в Lokalise
        """
        self.api_token = api_token
        self.project_id = project_id
        self.base_url = "https://api.lokalise.com/api2"
        self.logger = logging.getLogger(__name__)

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Выполняет запрос к API

        Args:
            endpoint: Endpoint API
            params: Параметры запроса

        Returns:
            Ответ API
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-Api-Token": self.api_token
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        return response.json()

    def fetch_keys_paginated(
        self,
        lang_iso: str = "ru",
        page: int = 1,
        limit: int = 500
    ) -> Dict:
        """
        Постранично выгружает ключи с переводами

        Args:
            lang_iso: ISO код языка
            page: Номер страницы
            limit: Количество записей на странице

        Returns:
            Словарь с ключами и метаданными
        """
        endpoint = f"/projects/{self.project_id}/keys"
        params = {
            "page": page,
            "limit": limit,
            "include_translations": 1,
            "filter_langs": lang_iso
        }

        return self._make_request(endpoint, params)

    def fetch_all_keys(self, lang_iso: str = "ru") -> List[TranslationKey]:
        """
        Выгружает все ключи переводов постранично

        Args:
            lang_iso: ISO код языка

        Returns:
            Список TranslationKey
        """
        all_keys = []
        page = 1

        while True:
            self.logger.info(f"Загрузка страницы {page}...")

            response = self.fetch_keys_paginated(lang_iso, page)
            keys_data = response.get("keys", [])

            if not keys_data:
                break

            # Преобразуем в TranslationKey
            for key_data in keys_data:
                translation_key = self._convert_to_translation_key(
                    key_data,
                    lang_iso
                )
                if translation_key:
                    all_keys.append(translation_key)

            # Проверяем, есть ли еще страницы
            page_info = response.get("x_pagination", {})
            current_page = page_info.get("page", page)
            total_pages = page_info.get("total_pages", current_page)

            if current_page >= total_pages:
                break

            page += 1

        self.logger.info(f"Загружено {len(all_keys)} ключей")
        return all_keys

    def _convert_to_translation_key(
        self,
        key_data: Dict,
        lang_iso: str
    ) -> Optional[TranslationKey]:
        """
        Преобразует данные из Lokalise в TranslationKey

        Args:
            key_data: Данные ключа из API
            lang_iso: ISO код языка

        Returns:
            TranslationKey или None
        """
        key_name = key_data.get("key_name", {}).get("web")
        if not key_name:
            return None

        # Извлекаем перевод
        translations = key_data.get("translations", [])
        translation_text = None
        modified_at = None

        for trans in translations:
            if trans.get("language_iso") == lang_iso:
                translation_text = trans.get("translation")
                modified_at = trans.get("modified_at")
                break

        if not translation_text:
            return None

        # Извлекаем путь к файлу
        file_path = key_data.get("filenames", {}).get("web", "unknown.ftl")

        # Извлекаем контекст
        context = key_data.get("description")

        return TranslationKey(
            key=key_name,
            file_path=file_path,
            translation=translation_text,
            modified_at=modified_at,
            context=context
        )

    def group_keys_by_file(
        self,
        keys: List[TranslationKey]
    ) -> Dict[str, List[TranslationKey]]:
        """
        Группирует ключи по базовому имени файла

        Args:
            keys: Список ключей

        Returns:
            Словарь {base_filename: [keys]}
        """
        grouped = defaultdict(list)

        for key in keys:
            # Извлекаем базовое имя файла
            file_path = Path(key.file_path)
            base_name = file_path.stem  # Имя без расширения

            grouped[base_name].append(key)

        return dict(grouped)
