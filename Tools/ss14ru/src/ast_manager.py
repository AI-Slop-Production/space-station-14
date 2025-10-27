"""
Менеджер для работы с Fluent AST
"""

from typing import List, Dict, Set, Tuple
from fluent.syntax import parse, serialize
from fluent.syntax.ast import Resource, Message
import logging


class ASTComparator:
    """Сравнитель Fluent AST"""

    def __init__(self):
        """Инициализация сравнителя"""
        self.logger = logging.getLogger(__name__)

    def extract_messages_dict(self, resource: Resource) -> Dict[str, Message]:
        """
        Извлекает словарь сообщений из Resource

        Args:
            resource: Fluent AST Resource

        Returns:
            Словарь {message_key: Message}
        """
        messages = {}
        for entry in resource.body:
            if isinstance(entry, Message):
                messages[entry.id.name] = entry
        return messages

    def compare_resources(
        self,
        source: Resource,
        target: Resource
    ) -> Dict[str, Set[str]]:
        """
        Сравнивает два Fluent Resource

        Args:
            source: Исходный ресурс
            target: Целевой ресурс

        Returns:
            Словарь с наборами ключей: matching, different, source_only, target_only
        """
        source_messages = self.extract_messages_dict(source)
        target_messages = self.extract_messages_dict(target)

        source_keys = set(source_messages.keys())
        target_keys = set(target_messages.keys())

        result = {
            'matching': set(),
            'different': set(),
            'source_only': source_keys - target_keys,
            'target_only': target_keys - source_keys
        }

        # Проверяем совпадающие ключи
        common_keys = source_keys & target_keys
        for key in common_keys:
            if self._messages_equal(source_messages[key], target_messages[key]):
                result['matching'].add(key)
            else:
                result['different'].add(key)

        return result

    def _messages_equal(self, msg1: Message, msg2: Message) -> bool:
        """Проверяет равенство двух сообщений"""
        # Сериализуем оба сообщения и сравниваем
        ser1 = serialize(msg1)
        ser2 = serialize(msg2)
        return ser1 == ser2


class ASTManager:
    """Менеджер для обновления Fluent AST"""

    def __init__(self):
        """Инициализация менеджера"""
        self.logger = logging.getLogger(__name__)

    def update_message(
        self,
        resource: Resource,
        message_key: str,
        new_message: Message
    ) -> bool:
        """
        Обновляет сообщение в Resource по ключу

        Args:
            resource: Fluent AST Resource
            message_key: Ключ сообщения для обновления
            new_message: Новое сообщение

        Returns:
            True если обновление произошло
        """
        for idx, entry in enumerate(resource.body):
            if isinstance(entry, Message) and entry.id.name == message_key:
                resource.body[idx] = new_message
                return True
        return False

    def add_message(self, resource: Resource, message: Message):
        """
        Добавляет сообщение в конец Resource

        Args:
            resource: Fluent AST Resource
            message: Сообщение для добавления
        """
        resource.body.append(message)

    def remove_message(self, resource: Resource, message_key: str) -> bool:
        """
        Удаляет сообщение из Resource

        Args:
            resource: Fluent AST Resource
            message_key: Ключ сообщения для удаления

        Returns:
            True если удаление произошло
        """
        for idx, entry in enumerate(resource.body):
            if isinstance(entry, Message) and entry.id.name == message_key:
                resource.body.pop(idx)
                return True
        return False

    def get_message(self, resource: Resource, message_key: str) -> Message:
        """
        Получает сообщение по ключу

        Args:
            resource: Fluent AST Resource
            message_key: Ключ сообщения

        Returns:
            Message или None
        """
        for entry in resource.body:
            if isinstance(entry, Message) and entry.id.name == message_key:
                return entry
        return None
