"""
Модели данных для локализации
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union


@dataclass
class LocalizableEntity:
    """
    Модель локализуемой сущности из YAML

    Attributes:
        entity_id: Уникальный идентификатор сущности
        name: Название сущности (опционально)
        description: Описание сущности (опционально)
        suffix: Суффикс сущности (опционально)
        parent: ID родительской сущности (опционально)
    """
    entity_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    suffix: Optional[str] = None
    parent: Optional[Union[str, List[str]]] = None

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> 'LocalizableEntity':
        """
        Создает LocalizableEntity из словаря YAML

        Args:
            data: Словарь с данными из YAML

        Returns:
            Экземпляр LocalizableEntity

        Raises:
            ValueError: Если отсутствует обязательное поле 'id'
        """
        if 'id' not in data:
            raise ValueError("YAML-сущность должна содержать поле 'id'")

        # Извлекаем родителя (сохраняем как есть: строку или список)
        parent = None
        if "parent" in data:
            parent_val = data["parent"]
            if isinstance(parent_val, (str, list)):
                parent = parent_val

        # Преобразуем значения в строки, если они существуют
        name_val = data.get('name')
        description_val = data.get('description')
        suffix_val = data.get('suffix')

        return cls(
            entity_id=str(data['id']),
            name=str(name_val) if name_val is not None else None,
            description=str(description_val) if description_val is not None else None,
            suffix=str(suffix_val) if suffix_val is not None else None,
            parent=parent
        )

    @classmethod
    def from_yaml_list(cls, yaml_data: List[Dict[str, Any]]) -> List['LocalizableEntity']:
        """
        Создает список LocalizableEntity из списка словарей YAML

        Args:
            yaml_data: Список словарей из YAML

        Returns:
            Список экземпляров LocalizableEntity
        """
        entities = []

        for item in yaml_data:
            if not isinstance(item, dict):
                continue

            try:
                entity = cls.from_yaml_dict(item)
                # Добавляем только если есть хотя бы одно локализуемое поле
                if entity.has_localizable_fields():
                    entities.append(entity)
            except (ValueError, KeyError):
                # Пропускаем некорректные сущности
                continue

        return entities

    def has_localizable_fields(self) -> bool:
        """
        Проверяет, есть ли у сущности локализуемые поля

        Returns:
            True если есть хотя бы одно локализуемое поле
        """
        return any([
            self.name is not None and self.name != '',
            self.description is not None and self.description != '',
            self.suffix is not None and self.suffix != ''
        ])

    def get_fluent_key_prefix(self) -> str:
        """
        Возвращает префикс для Fluent-ключей этой сущности

        Returns:
            Префикс ключа (например, "ent-MyEntity")
        """
        return f"ent-{self.entity_id}"

    def get_name_key(self) -> str:
        """Возвращает Fluent-ключ для поля name"""
        return f"{self.get_fluent_key_prefix()}"

    def get_description_key(self) -> str:
        """Возвращает Fluent-ключ для поля description"""
        return f"{self.get_fluent_key_prefix()}.desc"

    def get_suffix_key(self) -> str:
        """Возвращает Fluent-ключ для поля suffix"""
        return f"{self.get_fluent_key_prefix()}.suffix"


@dataclass
class FluentMessage:
    """
    Модель Fluent-сообщения для генерации

    Attributes:
        key: Ключ сообщения
        value: Значение сообщения
        comment: Комментарий к сообщению (опционально)
        attributes: Словарь атрибутов сообщения
    """
    key: str
    value: str
    comment: Optional[str] = None
    attributes: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """Инициализация после создания"""
        if self.attributes is None:
            self.attributes = {}


@dataclass
class TranslationKey:
    """
    Модель ключа перевода из внешней системы (например, Lokalise)

    Attributes:
        key: Полный ключ перевода (например, "ent-MyEntity.desc")
        file_path: Относительный путь к файлу локализации
        translation: Переведенный текст
        modified_at: Временная метка последнего изменения (опционально)
        context: Контекст перевода (опционально)
    """
    key: str
    file_path: str
    translation: str
    modified_at: Optional[str] = None
    context: Optional[str] = None

    def get_base_key(self) -> str:
        """
        Возвращает базовый ключ без атрибута

        Returns:
            Базовый ключ (например, "ent-MyEntity" из "ent-MyEntity.desc")
        """
        if '.' in self.key:
            return self.key.rsplit('.', 1)[0]
        return self.key

    def get_attribute_name(self) -> Optional[str]:
        """
        Возвращает имя атрибута если есть

        Returns:
            Имя атрибута или None
        """
        if '.' in self.key:
            return self.key.rsplit('.', 1)[1]
        return None

    def is_attribute(self) -> bool:
        """Проверяет, является ли ключ атрибутом"""
        return '.' in self.key
