"""
Компонент сериализации Fluent-сообщений
"""

from typing import List, Dict, Optional, Union
from fluent.syntax import ast, parse
from .models import LocalizableEntity, FluentMessage, TranslationKey


class FluentSerializer:
    """Сериализатор для создания Fluent-сообщений из различных источников"""

    def __init__(self):
        """Инициализация сериализатора"""
        pass

    def _parse_value_to_pattern(self, value: str) -> ast.Pattern:
        """
        Парсит строковое значение в Fluent Pattern AST

        Если значение содержит Fluent placeables (типа { "" } или { Parent }),
        парсит его как Fluent строку. Иначе создает простой TextElement.

        Args:
            value: Строковое значение для парсинга

        Returns:
            Fluent Pattern AST
        """
        # Если значение содержит { и }, парсим как Fluent
        if '{' in value and '}' in value:
            # Создаем временное Fluent сообщение для парсинга
            temp_fluent = f"temp = {value}"
            try:
                resource = parse(temp_fluent)
                # Извлекаем pattern из первого сообщения
                if resource.body and isinstance(resource.body[0], ast.Message):
                    return resource.body[0].value
            except:
                # Если парсинг не удался, используем как текст
                pass

        # По умолчанию создаем простой TextElement
        return ast.Pattern([ast.TextElement(value)])

    def _format_parent_reference(self, parent: Union[str, List[str]]) -> str:
        """
        Форматирует ссылку на родительское сообщение

        ВАЖНО: Fluent не поддерживает списки в ссылках { [A, B] }.
        Для списка родителей используем последнего (наиболее специфичный).
        Добавляем префикс "ent-" к parent ID, так как в Fluent файлах все entity имеют этот префикс.

        Args:
            parent: ID родителя (строка или список строк)

        Returns:
            Форматированная ссылка (например, "{ ent-ParentId }")
        """
        if isinstance(parent, str):
            return f"{{ ent-{parent} }}"
        elif isinstance(parent, list) and parent:
            # Берём последнего родителя из списка (наиболее специфичный)
            return f"{{ ent-{parent[-1]} }}"
        return "{ \"\" }"

    def _format_parent_attribute_reference(self, parent: Union[str, List[str]], attribute: str) -> str:
        """
        Форматирует ссылку на атрибут родительского сообщения

        ВАЖНО: Fluent не поддерживает списки в ссылках { [A.desc, B.desc] }.
        Для списка родителей используем последнего (наиболее специфичный).
        Добавляем префикс "ent-" к parent ID, так как в Fluent файлах все entity имеют этот префикс.

        Args:
            parent: ID родителя (строка или список строк)
            attribute: Имя атрибута (например, "desc")

        Returns:
            Форматированная ссылка (например, "{ ent-ParentId.desc }")
        """
        if isinstance(parent, str):
            return f"{{ ent-{parent}.{attribute} }}"
        elif isinstance(parent, list) and parent:
            # Берём последнего родителя из списка (наиболее специфичный)
            return f"{{ ent-{parent[-1]}.{attribute} }}"
        return "{ \"\" }"

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
        # ВАЖНО: Создаем запись ВСЕГДА, даже если нет полей
        # Даже если нет ни name, ни description, ни suffix, ни parent - создаем с { "" }
        # Потому что другие entity могут ссылаться на эту как на parent
        #
        # Пример: BaseGameRule (нет полей) <- CargoGiftsBase (parent: BaseGameRule)
        # Без записи BaseGameRule будет ошибка "Unknown message: ent-BaseGameRule"

        # Определяем значение name
        if entity.name is not None:
            value = entity.name
        elif use_parent_references and entity.parent:
            # Если нет name, но есть родитель - создаем ссылку
            value = self._format_parent_reference(entity.parent)
        else:
            # Если нет ни name, ни parent - пустая ссылка
            value = '{ "" }'

        # Собираем атрибуты
        attributes = {}

        # Description: если есть свое - используем, иначе ссылка на parent или пустая ссылка
        if entity.description is not None:
            attributes['desc'] = entity.description
        elif use_parent_references and entity.parent:
            # Если нет description, но есть parent - ссылка на parent.desc
            attributes['desc'] = self._format_parent_attribute_reference(entity.parent, 'desc')
        else:
            # Если нет ни description, ни parent - пустая ссылка
            attributes['desc'] = '{ "" }'

        # Suffix НЕ наследуется от parent
        # Проверяем, что suffix не None и не пустая строка
        if entity.suffix is not None and entity.suffix != '':
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
            # Парсим значение в Pattern (поддерживает placeables)
            message_value = self._parse_value_to_pattern(msg.value)

            # Создаем атрибуты если есть
            attributes = []
            if msg.attributes:
                for attr_name, attr_value in msg.attributes.items():
                    # Парсим каждый атрибут тоже
                    attr_pattern = self._parse_value_to_pattern(attr_value)
                    attributes.append(ast.Attribute(
                        id=ast.Identifier(attr_name),
                        value=attr_pattern
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
