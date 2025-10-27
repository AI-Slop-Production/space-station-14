"""
Объединяющий слой для слияния изменений из внешних источников
"""

from pathlib import Path
from typing import List, Dict
from fluent.syntax import parse
import logging

from .config import ProjectConfig
from .file_handlers import FluentFileHandler
from .fluent_formatter import FluentFormatter
from .ast_manager import ASTComparator, ASTManager
from .models import TranslationKey
from .fluent_serializer import FluentSerializer


class TranslationMerger:
    """Менеджер для слияния переводов из внешних источников"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация менеджера слияния

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.file_handler = FluentFileHandler()
        self.formatter = FluentFormatter()
        self.comparator = ASTComparator()
        self.ast_manager = ASTManager()
        self.serializer = FluentSerializer()
        self.logger = logging.getLogger(__name__)

    def merge_translations(
        self,
        target_file: Path,
        translation_keys: List[TranslationKey],
        warn_inconsistent: bool = True
    ) -> Dict[str, int]:
        """
        Объединяет переводы из внешнего источника с существующим файлом

        Args:
            target_file: Целевой файл для обновления
            translation_keys: Список ключей переводов
            warn_inconsistent: Предупреждать о несогласованных ключах

        Returns:
            Статистика изменений
        """
        stats = {
            'updated': 0,
            'added': 0,
            'removed': 0,
            'unchanged': 0,
            'warnings': 0
        }

        # Создаем файл если не существует
        if not target_file.exists():
            target_file.parent.mkdir(parents=True, exist_ok=True)
            # Создаем пустой ресурс
            from fluent.syntax.ast import Resource
            target_resource = Resource([])
        else:
            # Парсим существующий файл
            content = self.file_handler.read(target_file)
            target_resource = parse(content)

        # Преобразуем ключи переводов в Fluent сообщения
        new_messages_ast = self.serializer.translation_keys_to_messages(
            translation_keys,
            group_by_base_key=True
        )

        # Создаем ресурс из новых сообщений
        new_resource = self.serializer.messages_to_ast(new_messages_ast)

        # Сравниваем
        comparison = self.comparator.compare_resources(new_resource, target_resource)

        # Обрабатываем различия
        new_messages = self.comparator.extract_messages_dict(new_resource)

        # Обновляем существующие ключи
        for key in comparison['different']:
            if self.ast_manager.update_message(
                target_resource,
                key,
                new_messages[key]
            ):
                stats['updated'] += 1

        # Добавляем новые ключи
        for key in comparison['source_only']:
            self.ast_manager.add_message(target_resource, new_messages[key])
            stats['added'] += 1

        # Предупреждаем о ключах только в целевом файле
        if warn_inconsistent and comparison['target_only']:
            stats['warnings'] += len(comparison['target_only'])
            self.logger.warning(
                f"Ключи только в {target_file}: "
                f"{', '.join(sorted(comparison['target_only']))}"
            )

        # Неизменные ключи
        stats['unchanged'] = len(comparison['matching'])

        # Сохраняем если были изменения
        if stats['updated'] > 0 or stats['added'] > 0:
            formatted = self.formatter.format_ast(target_resource)
            self.file_handler.write(target_file, formatted)

            self.logger.info(
                f"Обновлен {target_file}: "
                f"+{stats['added']}, ~{stats['updated']}, "
                f"={stats['unchanged']}"
            )

        return stats

    def merge_all_translations(
        self,
        translations_by_file: Dict[str, List[TranslationKey]],
        warn_inconsistent: bool = True
    ) -> Dict[str, int]:
        """
        Объединяет переводы для множества файлов

        Args:
            translations_by_file: Словарь {filename: [translation_keys]}
            warn_inconsistent: Предупреждать о несогласованных ключах

        Returns:
            Общая статистика
        """
        total_stats = {
            'files_processed': 0,
            'total_updated': 0,
            'total_added': 0,
            'total_removed': 0,
            'total_unchanged': 0,
            'total_warnings': 0,
            'errors': 0
        }

        for filename, keys in translations_by_file.items():
            try:
                # Определяем путь к файлу
                target_file = self.config.ru_ru_locale / f"{filename}.ftl"

                stats = self.merge_translations(
                    target_file,
                    keys,
                    warn_inconsistent=warn_inconsistent
                )

                total_stats['files_processed'] += 1
                total_stats['total_updated'] += stats['updated']
                total_stats['total_added'] += stats['added']
                total_stats['total_removed'] += stats['removed']
                total_stats['total_unchanged'] += stats['unchanged']
                total_stats['total_warnings'] += stats['warnings']

            except Exception as e:
                self.logger.error(f"Ошибка слияния {filename}: {e}")
                total_stats['errors'] += 1

        return total_stats
