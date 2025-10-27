"""
Компонент сериализации Fluent-сообщений
"""

from typing import List, Dict, Optional, Union
from fluent.syntax import ast
from .models import LocalizableEntity, FluentMessage, TranslationKey


class FluentSerializer:
    """Сериализатор для создания Fluent-сообщений из различных источников"""

    def __init__(self):
        """Инициализация сериализатора"""
        pass

    def _format_parent_reference(self, parent: Union[str, List[str]]) -> str:
        """
        Форматирует ссылку на родительское сообщение

        Args:
            parent: ID родителя (строка или список строк)

        Returns:
            Форматированная ссылка (например, "{ ParentId }" или "{ [Parent1, Parent2] }")
        """
        if isinstance(parent, str):
            return f"{{ {parent} }}"
        elif isinstance(parent, list):
            parent_refs = ", ".join(parent)
            return f"{{ [{parent_refs}] }}"
        return ""

    def _format_parent_attribute_reference(self, parent: Union[str, List[str]], attribute: str) -> str:
        """
        Форматирует ссылку на атрибут родительского сообщения

        Args:
            parent: ID родителя (строка или список строк)
            attribute: Имя атрибута (например, "desc")

        Returns:
            Форматированная ссылка (например, "{ ParentId.desc }" или "{ [Parent1.desc, Parent2.desc] }")
        """
        if isinstance(parent, str):
            return f"{{ {parent}.{attribute} }}"
        elif isinstance(parent, list):
            parent_refs = ", ".join([f"{p}.{attribute}" for p in parent])
            return f"{{ [{parent_refs}] }}"
        return ""

    def entity_to_messages(
        self,
        entity: LocalizableEntity,
        add_comments: bool = True,
        use_parent_references: bool = True
    ) -> List[FluentMessage]:
        """
        Преобразует LocalizableEntity в список Fluent-сообщений

        Args:
            entity: Сущность для преобразования
            add_comments: Добавлять ли комментарии с описанием (НЕ ИСПОЛЬЗУЕТСЯ - для совместимости)
            use_parent_references: Использовать ли ссылки на родительские значения

        Returns:
            Список FluentMessage (всегда один элемент)
        """
        # Определяем значение name
        if entity.name is not None:
            value = entity.name
        elif use_parent_references and entity.parent:
            # Если нет name, но есть родитель - создаем ссылку
            value = self._format_parent_reference(entity.parent)
        else:
            # Пропускаем сущности без name и без parent
            return []

        # Собираем атрибуты
        attributes = {}

        # Description: если есть свое - используем, иначе ссылка на parent
        if entity.description is not None:
            attributes['desc'] = entity.description
        elif use_parent_references and entity.parent:
            # Если нет description, но есть parent - ссылка на parent.desc
            attributes['desc'] = self._format_parent_attribute_reference(entity.parent, 'desc')

        # Suffix НЕ наследуется от parent
        if entity.suffix is not None:
            attributes['suffix'] = entity.suffix

        # Создаем одно сообщение с атрибутами
        return [FluentMessage(
            key=entity.get_name_key(),
            value=value,
            comment=None,  # Комментарии не нужны
            attributes=attributes if attributes else None
        )]

    def entities_to_messages(
        self,
        entities: List[LocalizableEntity],
        add_comments: bool = True,
        use_parent_references: bool = True
    ) -> List[FluentMessage]:
        """
        Преобразует список сущностей в список Fluent-сообщений

        Args:
            entities: Список сущностей
            add_comments: Добавлять ли комментарии
            use_parent_references: Использовать ли ссылки на родителей

        Returns:
            Список FluentMessage
        """
        all_messages = []

        for entity in entities:
            messages = self.entity_to_messages(
                entity,
                add_comments=add_comments,
                use_parent_references=use_parent_references
            )
            all_messages.extend(messages)

        return all_messages

    def translation_keys_to_messages(
        self,
        keys: List[TranslationKey],
        group_by_base_key: bool = True
    ) -> List[FluentMessage]:
        """
        Преобразует ключи переводов в Fluent-сообщения

        Args:
            keys: Список ключей переводов
            group_by_base_key: Группировать ли атрибуты с основным ключом

        Returns:
            Список FluentMessage
        """
        if not group_by_base_key:
            # Простое преобразование без группировки
            messages = []
            for key in keys:
                messages.append(FluentMessage(
                    key=key.key,
                    value=key.translation,
                    comment=key.context
                ))
            return messages

        # Группировка: собираем атрибуты вместе с основным сообщением
        grouped: Dict[str, Dict[str, any]] = {}

        for key in keys:
            base_key = key.get_base_key()

            if base_key not in grouped:
                grouped[base_key] = {
                    'value': None,
                    'comment': None,
                    'attributes': {}
                }

            if key.is_attribute():
                # Это атрибут
                attr_name = key.get_attribute_name()
                grouped[base_key]['attributes'][attr_name] = key.translation
            else:
                # Это основное сообщение
                grouped[base_key]['value'] = key.translation
                if key.context:
                    grouped[base_key]['comment'] = key.context

        # Преобразуем сгруппированные данные в FluentMessage
        messages = []
        for base_key, data in grouped.items():
            if data['value'] is not None:
                messages.append(FluentMessage(
                    key=base_key,
                    value=data['value'],
                    comment=data['comment'],
                    attributes=data['attributes'] if data['attributes'] else None
                ))

        return messages

    def messages_to_ast(self, messages: List[FluentMessage]) -> ast.Resource:
        """
        Преобразует список FluentMessage в Fluent AST Resource

        Args:
            messages: Список сообщений

        Returns:
            Fluent AST Resource
        """
        entries = []

        for msg in messages:
            # Создаем основное сообщение
            message_value = ast.Pattern([
                ast.TextElement(msg.value)
            ])

            # Создаем атрибуты если есть
            attributes = []
            if msg.attributes:
                for attr_name, attr_value in msg.attributes.items():
                    attributes.append(ast.Attribute(
                        id=ast.Identifier(attr_name),
                        value=ast.Pattern([
                            ast.TextElement(attr_value)
                        ])
                    ))

            # Создаем Message
            message = ast.Message(
                id=ast.Identifier(msg.key),
                value=message_value,
                attributes=attributes if attributes else None
            )

            entries.append(message)

        return ast.Resource(entries)

    def entities_to_ast(
        self,
        entities: List[LocalizableEntity],
        add_comments: bool = True,
        use_parent_references: bool = True
    ) -> ast.Resource:
        """
        Преобразует список сущностей напрямую в Fluent AST

        Args:
            entities: Список сущностей
            add_comments: Добавлять ли комментарии
            use_parent_references: Использовать ли ссылки на родителей

        Returns:
            Fluent AST Resource
        """
        messages = self.entities_to_messages(
            entities,
            add_comments=add_comments,
            use_parent_references=use_parent_references
        )
        return self.messages_to_ast(messages)
