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
        # Добавляем безопасный конструктор для всех неизвестных тегов SS14
        # Это позволяет игнорировать теги типа !type:ActionAnomalyPulseEvent
        yaml.add_multi_constructor('!type:', self._unknown_constructor, Loader=yaml.SafeLoader)

    def _unknown_constructor(self, loader, tag_suffix, node):
        """
        Конструктор для обработки неизвестных тегов SS14

        Args:
            loader: YAML загрузчик
            tag_suffix: Суффикс тега (например, ActionAnomalyPulseEvent)
            node: Узел YAML

        Returns:
            Словарь с данными узла
        """
        if isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        elif isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        else:
            return loader.construct_scalar(node)

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

        ВАЖНО: Обрабатываются только прототипы с type: entity
        Все остальные типы (trait, recipe, и т.д.) пропускаются

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
            # ВАЖНО: Обрабатываем только type: entity
            entity_type = entity.get('type')
            if entity_type != 'entity':
                continue

            # ВАЖНО: Добавляем ВСЕ entity независимо от наличия полей
            # Даже если нет ни name, ни description, ни parent - создаем запись с { "" }
            # Потому что другие entity могут ссылаться на эту как на parent
            #
            # Пример: BaseGameRule (нет полей) <- CargoGiftsBase (ссылается на parent)
            # Если не создать BaseGameRule, то CargoGiftsBase будет ссылаться на несуществующий ключ
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

    def extract_parent(self, entity: Dict[str, Any]):
        """
        Извлекает родительский прототип из поля 'parent'

        Args:
            entity: Словарь сущности

        Returns:
            ID родительского прототипа (str), список ID (List[str]) или None
        """
        # Проверяем поле 'parent'
        if "parent" in entity:
            parent = entity["parent"]
            # parent может быть строкой или списком - возвращаем как есть
            if isinstance(parent, (str, list)):
                return parent

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
