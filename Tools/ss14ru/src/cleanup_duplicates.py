"""
Утилита для удаления дублирующихся блоков сущностей в Fluent-файлах
"""

from pathlib import Path
from typing import List, Dict, Set
from fluent.syntax import parse
from fluent.syntax.ast import Message, Resource, Comment
import logging

from .config import ProjectConfig
from .file_handlers import FluentFileHandler
from .fluent_formatter import FluentFormatter


class DuplicateCleaner:
    """Очистка дублирующихся сообщений в Fluent-файлах"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация очистителя

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.file_handler = FluentFileHandler()
        self.formatter = FluentFormatter()
        self.logger = logging.getLogger(__name__)

    def find_duplicates(self, resource: Resource) -> Dict[str, List[int]]:
        """
        Находит дублирующиеся сообщения в AST

        Args:
            resource: Fluent AST Resource

        Returns:
            Словарь {message_key: [index1, index2, ...]}
        """
        key_positions: Dict[str, List[int]] = {}

        for idx, entry in enumerate(resource.body):
            if isinstance(entry, Message):
                key = entry.id.name
                if key not in key_positions:
                    key_positions[key] = []
                key_positions[key].append(idx)

        # Оставляем только дубликаты (где больше одной позиции)
        duplicates = {k: v for k, v in key_positions.items() if len(v) > 1}

        return duplicates

    def remove_duplicates(
        self,
        resource: Resource,
        keep_first: bool = True
    ) -> tuple[Resource, int]:
        """
        Удаляет дубликаты из AST, сохраняя первое или последнее вхождение

        Args:
            resource: Fluent AST Resource
            keep_first: Сохранять первое вхождение (True) или последнее (False)

        Returns:
            Кортеж (новый Resource, количество удаленных дубликатов)
        """
        duplicates = self.find_duplicates(resource)

        if not duplicates:
            return resource, 0

        # Определяем индексы для удаления
        indices_to_remove: Set[int] = set()

        for key, positions in duplicates.items():
            if keep_first:
                # Удаляем все кроме первого
                indices_to_remove.update(positions[1:])
            else:
                # Удаляем все кроме последнего
                indices_to_remove.update(positions[:-1])

        # Создаем новый список entries без дубликатов
        new_body = []
        removed_count = 0

        for idx, entry in enumerate(resource.body):
            if idx in indices_to_remove:
                removed_count += 1
                # Также удаляем комментарий перед сообщением если есть
                if new_body and isinstance(new_body[-1], Comment):
                    new_body.pop()
            else:
                new_body.append(entry)

        resource.body = new_body

        return resource, removed_count

    def clean_file(
        self,
        file_path: Path,
        keep_first: bool = True,
        dry_run: bool = False
    ) -> int:
        """
        Очищает файл от дубликатов

        Args:
            file_path: Путь к файлу
            keep_first: Сохранять первое вхождение
            dry_run: Только показать, что будет удалено

        Returns:
            Количество удаленных дубликатов
        """
        if not file_path.exists():
            return 0

        # Парсим файл
        content = self.file_handler.read(file_path)
        resource = parse(content)

        # Находим дубликаты
        duplicates = self.find_duplicates(resource)

        if not duplicates:
            return 0

        if dry_run:
            self.logger.info(
                f"[DRY RUN] {file_path}: найдено {len(duplicates)} дублирующихся ключей"
            )
            for key, positions in duplicates.items():
                self.logger.info(f"  - {key}: {len(positions)} вхождений")
            return len(duplicates)

        # Удаляем дубликаты
        resource, removed_count = self.remove_duplicates(resource, keep_first)

        if removed_count > 0:
            # Форматируем и сохраняем
            formatted = self.formatter.format_ast(resource)
            self.file_handler.write(file_path, formatted)

            self.logger.info(f"Очищен {file_path}: удалено {removed_count} дубликатов")

        return removed_count

    def clean_all(
        self,
        locale_dir: Path = None,
        keep_first: bool = True,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Очищает все файлы в указанной локали

        Args:
            locale_dir: Директория локали (по умолчанию ru-RU)
            keep_first: Сохранять первое вхождение
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        if locale_dir is None:
            locale_dir = self.config.ru_ru_locale

        stats = {
            'files_processed': 0,
            'files_with_duplicates': 0,
            'total_duplicates_removed': 0,
            'errors': 0
        }

        ftl_files = self.config.get_fluent_files(locale_dir)

        if dry_run:
            self.logger.info("[DRY RUN MODE] Предпросмотр изменений:")

        for ftl_file in ftl_files:
            try:
                removed = self.clean_file(ftl_file, keep_first, dry_run)
                stats['files_processed'] += 1

                if removed > 0:
                    stats['files_with_duplicates'] += 1
                    stats['total_duplicates_removed'] += removed

            except Exception as e:
                self.logger.error(f"Ошибка очистки {ftl_file}: {e}")
                stats['errors'] += 1

        return stats
