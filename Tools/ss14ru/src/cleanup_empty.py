"""
Утилита для очистки пустых файлов и директорий
"""

from pathlib import Path
from typing import List, Dict
from fluent.syntax import parse
from fluent.syntax.ast import Message, Term
import logging

from .config import ProjectConfig


class EmptyCleaner:
    """Очистка пустых файлов и директорий"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация очистителя

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def is_file_empty(self, file_path: Path) -> bool:
        """
        Проверяет, является ли Fluent-файл пустым

        Args:
            file_path: Путь к файлу

        Returns:
            True если файл пустой (нет сообщений и терминов)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Убираем BOM если есть
            if content.startswith('\ufeff'):
                content = content[1:]

            # Если файл полностью пустой
            if not content.strip():
                return True

            # Парсим и проверяем наличие сообщений и терминов
            resource = parse(content)
            messages = [entry for entry in resource.body if isinstance(entry, Message)]
            terms = [entry for entry in resource.body if isinstance(entry, Term)]

            # Файл пустой, только если нет ни сообщений, ни терминов
            return len(messages) == 0 and len(terms) == 0

        except Exception as e:
            self.logger.error(f"Ошибка проверки файла {file_path}: {e}")
            return False

    def find_empty_files(self, locale_dir: Path) -> List[Path]:
        """
        Находит все пустые файлы в директории

        Args:
            locale_dir: Директория для поиска

        Returns:
            Список путей к пустым файлам
        """
        empty_files = []

        ftl_files = self.config.get_fluent_files(locale_dir)

        for ftl_file in ftl_files:
            if self.is_file_empty(ftl_file):
                empty_files.append(ftl_file)

        return empty_files

    def find_empty_directories(self, locale_dir: Path) -> List[Path]:
        """
        Находит все пустые директории

        Args:
            locale_dir: Корневая директория для поиска

        Returns:
            Список путей к пустым директориям
        """
        empty_dirs = []

        # Рекурсивно обходим все директории
        for dirpath in locale_dir.rglob('*'):
            if dirpath.is_dir():
                # Проверяем, пустая ли директория
                if not any(dirpath.iterdir()):
                    empty_dirs.append(dirpath)

        # Сортируем от самых глубоких к корню
        # (чтобы удалять снизу вверх)
        empty_dirs.sort(key=lambda p: len(p.parts), reverse=True)

        return empty_dirs

    def clean_empty_files(
        self,
        locale_dir: Path = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Удаляет пустые файлы

        Args:
            locale_dir: Директория локали (по умолчанию ru-RU)
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        if locale_dir is None:
            locale_dir = self.config.ru_ru_locale

        stats = {
            'files_deleted': 0,
            'errors': 0
        }

        empty_files = self.find_empty_files(locale_dir)

        if dry_run:
            self.logger.info(f"[DRY RUN] Найдено {len(empty_files)} пустых файлов:")
            for file_path in empty_files:
                self.logger.info(f"  - {file_path}")
            return stats

        for file_path in empty_files:
            try:
                file_path.unlink()
                stats['files_deleted'] += 1
                self.logger.info(f"Удален пустой файл: {file_path}")
            except Exception as e:
                self.logger.error(f"Ошибка удаления {file_path}: {e}")
                stats['errors'] += 1

        return stats

    def clean_empty_directories(
        self,
        locale_dir: Path = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Удаляет пустые директории

        Args:
            locale_dir: Директория локали (по умолчанию ru-RU)
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        if locale_dir is None:
            locale_dir = self.config.ru_ru_locale

        stats = {
            'dirs_deleted': 0,
            'errors': 0
        }

        empty_dirs = self.find_empty_directories(locale_dir)

        if dry_run:
            self.logger.info(f"[DRY RUN] Найдено {len(empty_dirs)} пустых директорий:")
            for dir_path in empty_dirs:
                self.logger.info(f"  - {dir_path}")
            return stats

        for dir_path in empty_dirs:
            try:
                dir_path.rmdir()
                stats['dirs_deleted'] += 1
                self.logger.info(f"Удалена пустая директория: {dir_path}")
            except Exception as e:
                self.logger.error(f"Ошибка удаления {dir_path}: {e}")
                stats['errors'] += 1

        return stats

    def clean_all(
        self,
        locale_dir: Path = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Удаляет все пустые файлы и директории

        Args:
            locale_dir: Директория локали (по умолчанию ru-RU)
            dry_run: Режим предпросмотра

        Returns:
            Общая статистика
        """
        if locale_dir is None:
            locale_dir = self.config.ru_ru_locale

        # Сначала удаляем пустые файлы
        file_stats = self.clean_empty_files(locale_dir, dry_run)

        # Затем удаляем пустые директории
        dir_stats = self.clean_empty_directories(locale_dir, dry_run)

        # Объединяем статистику
        return {
            'files_deleted': file_stats['files_deleted'],
            'dirs_deleted': dir_stats['dirs_deleted'],
            'errors': file_stats['errors'] + dir_stats['errors']
        }
