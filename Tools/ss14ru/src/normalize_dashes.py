"""
Утилита для нормализации тире в Fluent-файлах
"""

from pathlib import Path
from typing import Dict
import re
import logging

from .config import ProjectConfig
from .file_handlers import FluentFileHandler


class DashNormalizer:
    """Нормализатор тире между пробелами"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация нормализатора

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.file_handler = FluentFileHandler()
        self.logger = logging.getLogger(__name__)

        # Регулярное выражение для поиска дефисов между пробелами
        # НЕ заменяем в комментариях (строки начинающиеся с #)
        # НЕ заменяем в маркерах списков (строки начинающиеся с -)
        self.dash_pattern = re.compile(r'(?<= )-(?= )')

    def normalize_content(self, content: str) -> tuple[str, int]:
        """
        Нормализует тире в содержимом файла

        Args:
            content: Содержимое файла

        Returns:
            Кортеж (нормализованное содержимое, количество замен)
        """
        lines = content.split('\n')
        normalized_lines = []
        replacements_count = 0

        for line in lines:
            # Пропускаем комментарии
            if line.strip().startswith('#'):
                normalized_lines.append(line)
                continue

            # Пропускаем маркеры списков (строки начинающиеся с пробелов и -)
            if line.lstrip().startswith('-') and line.startswith((' ', '\t')):
                normalized_lines.append(line)
                continue

            # Заменяем дефис между пробелами на длинное тире
            new_line, count = self.dash_pattern.subn('—', line)
            normalized_lines.append(new_line)
            replacements_count += count

        return '\n'.join(normalized_lines), replacements_count

    def normalize_file(
        self,
        file_path: Path,
        dry_run: bool = False
    ) -> int:
        """
        Нормализует тире в файле

        Args:
            file_path: Путь к файлу
            dry_run: Режим предпросмотра

        Returns:
            Количество произведенных замен
        """
        if not file_path.exists():
            return 0

        try:
            # Читаем файл
            content = self.file_handler.read(file_path)

            # Нормализуем
            normalized, replacements = self.normalize_content(content)

            if replacements == 0:
                return 0

            if dry_run:
                self.logger.info(
                    f"[DRY RUN] {file_path}: будет произведено {replacements} замен"
                )
                return replacements

            # Сохраняем изменения
            self.file_handler.write(file_path, normalized)

            self.logger.info(
                f"Нормализован {file_path}: {replacements} замен"
            )

            return replacements

        except Exception as e:
            self.logger.error(f"Ошибка нормализации {file_path}: {e}")
            return 0

    def normalize_all(
        self,
        locale_dir: Path = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Нормализует тире во всех файлах

        Args:
            locale_dir: Директория локали (по умолчанию ru-RU)
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        if locale_dir is None:
            locale_dir = self.config.ru_ru_locale

        stats = {
            'files_processed': 0,
            'files_modified': 0,
            'total_replacements': 0,
            'errors': 0
        }

        ftl_files = self.config.get_fluent_files(locale_dir)

        if dry_run:
            self.logger.info("[DRY RUN MODE] Предпросмотр изменений:")

        for ftl_file in ftl_files:
            try:
                replacements = self.normalize_file(ftl_file, dry_run)
                stats['files_processed'] += 1

                if replacements > 0:
                    stats['files_modified'] += 1
                    stats['total_replacements'] += replacements

            except Exception as e:
                self.logger.error(f"Ошибка обработки {ftl_file}: {e}")
                stats['errors'] += 1

        return stats
