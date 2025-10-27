"""
Компонент сериализации Fluent-сообщений
"""

from typing import List, Dict, Optional
from fluent.syntax import ast
from .models import LocalizableEntity, FluentMessage, TranslationKey


class FluentSerializer:
    """Сериализатор для создания Fluent-сообщений из различных источников"""

    def __init__(self):
        """Инициализация сериализатора"""
        pass

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
            add_comments: Добавлять ли комментарии с описанием
            use_parent_references: Использовать ли ссылки на родительские значения

        Returns:
            Список FluentMessage
        """
        messages = []

        # Генерируем комментарий если нужно
        comment = None
        if add_comments:
            comment = f"Entity: {entity.entity_id}"
            if entity.parent:
                comment += f" (Parent: {entity.parent})"

        # Основное сообщение (name)
        if entity.name is not None:
            messages.append(FluentMessage(
                key=entity.get_name_key(),
                value=entity.name,
                comment=comment
            ))
        elif use_parent_references and entity.parent:
            # Если нет name, но есть родитель - создаем ссылку
            messages.append(FluentMessage(
                key=entity.get_name_key(),
                value=f"{{ ent-{entity.parent} }}",
                comment=comment
            ))

        # Атрибут description
        if entity.description is not None:
            # Для description комментарий не нужен (он уже есть у основного сообщения)
            messages.append(FluentMessage(
                key=entity.get_description_key(),
                value=entity.description
            ))

        # Атрибут suffix
        if entity.suffix is not None:
            messages.append(FluentMessage(
                key=entity.get_suffix_key(),
                value=entity.suffix
            ))

        return messages

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
            # Добавляем комментарий если есть
            if msg.comment:
                comment_lines = msg.comment.split('\n')
                for line in comment_lines:
                    entries.append(ast.Comment(content=line))

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

            # Добавляем пустую строку после каждого сообщения (для читаемости)
            entries.append(ast.Junk(" \n"))

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
