"""
Процессор для обработки YAML-прототипов и генерации Fluent-файлов
"""

from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import logging
from fluent.syntax import parse, ast

from .config import ProjectConfig
from .yaml_handler import YAMLHandler
from .models import LocalizableEntity
from .fluent_serializer import FluentSerializer
from .fluent_formatter import FluentFormatter
from .file_handlers import FluentFileHandler


class YAMLProcessor:
    """Процессор для сканирования YAML и генерации Fluent-локализации"""

    def __init__(self, config: ProjectConfig, force_overwrite: bool = False):
        """
        Инициализация процессора

        Args:
            config: Конфигурация проекта
            force_overwrite: Принудительная перезапись существующих файлов
        """
        self.config = config
        self.yaml_handler = YAMLHandler()
        self.serializer = FluentSerializer()
        self.formatter = FluentFormatter()
        self.file_handler = FluentFileHandler()
        self.logger = logging.getLogger(__name__)
        self.force_overwrite = force_overwrite

    def process_yaml_file(self, yaml_path: Path) -> List[LocalizableEntity]:
        """
        Обрабатывает один YAML-файл и извлекает локализуемые сущности

        ВАЖНО: Обрабатываются только прототипы с type: entity

        Args:
            yaml_path: Путь к YAML-файлу

        Returns:
            Список LocalizableEntity
        """
        try:
            # Извлекаем локализуемые сущности (только type: entity)
            yaml_entities = self.yaml_handler.extract_localizable_entities(yaml_path)

            # Преобразуем в модели
            entities = LocalizableEntity.from_yaml_list(yaml_entities)

            return entities

        except Exception as e:
            self.logger.error(f"Ошибка обработки {yaml_path}: {e}")
            return []

    def group_yaml_files_by_locale_path(self) -> Dict[Path, List[Path]]:
        """
        Группирует YAML-файлы по целевым путям локализации

        Returns:
            Словарь {locale_path: [yaml_file1, yaml_file2, ...]}
        """
        yaml_files = self.config.get_prototype_files()
        grouped = defaultdict(list)

        for yaml_file in yaml_files:
            locale_path = self.config.get_locale_path_from_prototype(yaml_file)
            grouped[locale_path].append(yaml_file)

        return dict(grouped)

    def merge_with_existing(
        self,
        new_resource: ast.Resource,
        existing_path: Path
    ) -> tuple[ast.Resource, int]:
        """
        Объединяет новый AST с существующим файлом

        Добавляет только те ключи из new_resource, которых нет в existing_path.
        Сохраняет все существующие переводы без изменений.

        Args:
            new_resource: Новый Fluent AST Resource с ключами из YAML
            existing_path: Путь к существующему Fluent-файлу

        Returns:
            Кортеж (merged_resource, added_count): объединённый AST и количество добавленных ключей
        """
        # Если файл не существует, возвращаем новый как есть
        if not existing_path.exists():
            # Подсчитываем количество сообщений
            message_count = sum(1 for entry in new_resource.body if isinstance(entry, ast.Message))
            return new_resource, message_count

        # Читаем существующий файл
        existing_content = self.file_handler.read(existing_path)
        existing_resource = parse(existing_content)

        # Собираем все существующие ключи
        existing_keys = set()
        for entry in existing_resource.body:
            if isinstance(entry, ast.Message):
                existing_keys.add(entry.id.name)

        # Фильтруем новые сообщения - берём только те, которых нет
        new_messages = []
        added_count = 0
        for entry in new_resource.body:
            if isinstance(entry, ast.Message):
                if entry.id.name not in existing_keys:
                    new_messages.append(entry)
                    added_count += 1

        # Если нет новых сообщений, возвращаем существующий без изменений
        if not new_messages:
            return existing_resource, 0

        # Добавляем новые сообщения в конец существующего файла
        merged_body = list(existing_resource.body) + new_messages
        merged_resource = ast.Resource(merged_body)

        return merged_resource, added_count

    def generate_fluent_for_group(
        self,
        yaml_files: List[Path],
        output_path: Path
    ) -> bool:
        """
        Генерирует или обновляет Fluent-файл для группы YAML-файлов

        Если файл существует и force_overwrite=False, добавляет только новые ключи.
        Если файл не существует или force_overwrite=True, создаёт файл заново.

        Args:
            yaml_files: Список YAML-файлов для обработки
            output_path: Путь к выходному Fluent-файлу

        Returns:
            True если успешно
        """
        all_entities = []

        # Собираем все сущности из всех файлов
        for yaml_file in yaml_files:
            entities = self.process_yaml_file(yaml_file)
            all_entities.extend(entities)

        if not all_entities:
            # Если нет новых сущностей и файл существует - это нормально
            if output_path.exists():
                return True
            self.logger.info(f"Нет локализуемых сущностей для {output_path}")
            return False

        # Генерируем Fluent AST из сущностей
        new_resource = self.serializer.entities_to_ast(
            all_entities,
            add_comments=True,
            use_parent_references=True
        )

        # Создаем директорию если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Объединяем с существующим файлом или используем новый
        if self.force_overwrite or not output_path.exists():
            # Режим полной перезаписи или файл не существует
            final_resource = new_resource
            entity_count = len(all_entities)

            if output_path.exists():
                self.logger.warning(f"Перезаписан {output_path} (force_overwrite=True)")
            else:
                self.logger.info(f"Создан {output_path} ({entity_count} ключей)")
        else:
            # Безопасный режим: добавляем только новые ключи
            final_resource, added_count = self.merge_with_existing(new_resource, output_path)

            if added_count > 0:
                self.logger.info(f"Обновлён {output_path} (+{added_count} новых ключей)")
            else:
                self.logger.debug(f"Без изменений {output_path} (все ключи уже существуют)")
                return True

        # Форматируем и сохраняем
        formatted = self.formatter.format_ast(final_resource)
        self.file_handler.write(output_path, formatted)

        return True

    def generate_all_locales(self) -> Dict[str, int]:
        """
        Генерирует или обновляет все Fluent-файлы из YAML-прототипов в ru-RU

        В безопасном режиме (force_overwrite=False) только добавляет новые ключи.
        В режиме перезаписи (force_overwrite=True) создаёт файлы заново.

        Returns:
            Статистика {status: count}
        """
        stats = {
            'created': 0,     # Созданные файлы
            'updated': 0,     # Обновлённые файлы (добавлены ключи)
            'skipped': 0,     # Пропущенные (нет изменений)
            'errors': 0       # Ошибки
        }

        # Группируем файлы
        grouped = self.group_yaml_files_by_locale_path()

        mode_str = "перезаписи" if self.force_overwrite else "безопасном"
        self.logger.info(f"Обработка {len(grouped)} групп файлов в режиме {mode_str}...")

        for locale_path, yaml_files in grouped.items():
            try:
                file_existed = locale_path.exists()

                # Генерируем или обновляем Fluent-файл
                success = self.generate_fluent_for_group(yaml_files, locale_path)

                if success:
                    if not file_existed:
                        stats['created'] += 1
                    elif self.force_overwrite:
                        stats['updated'] += 1
                    else:
                        # Файл существовал, добавлены ключи или без изменений
                        stats['updated'] += 1
                else:
                    stats['skipped'] += 1

            except Exception as e:
                self.logger.error(f"Ошибка генерации для {locale_path}: {e}")
                stats['errors'] += 1

        return stats

    def process_single_yaml(self, yaml_path: Path) -> bool:
        """
        Обрабатывает один YAML-файл и генерирует/обновляет соответствующий Fluent

        Args:
            yaml_path: Путь к YAML-файлу

        Returns:
            True если успешно
        """
        locale_path = self.config.get_locale_path_from_prototype(yaml_path)

        # Находим все YAML-файлы, которые должны попасть в этот Fluent-файл
        grouped = self.group_yaml_files_by_locale_path()
        yaml_files = grouped.get(locale_path, [yaml_path])

        return self.generate_fluent_for_group(yaml_files, locale_path)


def setup_logging(verbose: bool = False):
    """
    Настраивает логирование

    Args:
        verbose: Включить подробный вывод
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
