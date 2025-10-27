"""
YAML-адаптер для работы с прототипами
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml


class YAMLHandler:
    """Обработчик для чтения и фильтрации YAML-файлов"""

    def __init__(self):
        """Инициализация обработчика YAML"""
        pass

    def load(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        Загружает YAML-файл с использованием безопасного загрузчика

        Args:
            file_path: Путь к YAML-файлу

        Returns:
            Список словарей с данными из YAML
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # YAML может вернуть None для пустого файла
        if data is None:
            return []

        # Если данные не список, оборачиваем в список
        if not isinstance(data, list):
            return [data]

        return data

    def filter_entities(
        self,
        data: List[Dict[str, Any]],
        required_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Фильтрует элементы YAML, оставляя только нужные

        Args:
            data: Список словарей из YAML
            required_fields: Список обязательных полей (по умолчанию ["id"])

        Returns:
            Отфильтрованный список словарей
        """
        if required_fields is None:
            required_fields = ["id"]

        filtered = []

        for item in data:
            if not isinstance(item, dict):
                continue

            # Проверяем наличие всех обязательных полей
            if all(field in item for field in required_fields):
                filtered.append(item)

        return filtered

    def extract_localizable_entities(
        self,
        file_path: Path,
        extract_name: bool = True,
        extract_description: bool = True,
        extract_suffix: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Извлекает сущности, подходящие для локализации

        Args:
            file_path: Путь к YAML-файлу
            extract_name: Извлекать ли поле name
            extract_description: Извлекать ли поле description
            extract_suffix: Извлекать ли поле suffix

        Returns:
            Список словарей с локализуемыми сущностями
        """
        data = self.load(file_path)
        entities = self.filter_entities(data)

        localizable = []

        for entity in entities:
            # Проверяем, есть ли хотя бы одно локализуемое поле
            has_localizable = False

            if extract_name and "name" in entity:
                has_localizable = True
            if extract_description and "description" in entity:
                has_localizable = True
            if extract_suffix and "suffix" in entity:
                has_localizable = True

            if has_localizable:
                localizable.append(entity)

        return localizable

    def get_field_value(
        self,
        entity: Dict[str, Any],
        field: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Получает значение поля из сущности

        Args:
            entity: Словарь сущности
            field: Имя поля
            default: Значение по умолчанию

        Returns:
            Значение поля или default
        """
        return entity.get(field, default)

    def extract_parent(self, entity: Dict[str, Any]) -> Optional[str]:
        """
        Извлекает родительский прототип (parent или type)

        Args:
            entity: Словарь сущности

        Returns:
            ID родительского прототипа или None
        """
        # Сначала проверяем поле 'parent'
        if "parent" in entity:
            parent = entity["parent"]
            # parent может быть строкой или списком
            if isinstance(parent, str):
                return parent
            elif isinstance(parent, list) and parent:
                # Берем последнего родителя из списка
                return parent[-1]

        # Затем проверяем поле 'type'
        if "type" in entity:
            return entity["type"]

        return None

    def load_and_extract(
        self,
        file_path: Path,
        extract_name: bool = True,
        extract_description: bool = True,
        extract_suffix: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Загружает YAML-файл и извлекает локализуемые сущности одним вызовом

        Args:
            file_path: Путь к YAML-файлу
            extract_name: Извлекать ли поле name
            extract_description: Извлекать ли поле description
            extract_suffix: Извлекать ли поле suffix

        Returns:
            Список локализуемых сущностей
        """
        return self.extract_localizable_entities(
            file_path,
            extract_name=extract_name,
            extract_description=extract_description,
            extract_suffix=extract_suffix
        )
