"""
Процессор для обработки YAML-прототипов и генерации Fluent-файлов
"""

from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import logging

from .config import ProjectConfig
from .yaml_handler import YAMLHandler
from .models import LocalizableEntity
from .fluent_serializer import FluentSerializer
from .fluent_formatter import FluentFormatter
from .file_handlers import FluentFileHandler


class YAMLProcessor:
    """Процессор для сканирования YAML и генерации Fluent-локализации"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация процессора

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.yaml_handler = YAMLHandler()
        self.serializer = FluentSerializer()
        self.formatter = FluentFormatter()
        self.file_handler = FluentFileHandler()
        self.logger = logging.getLogger(__name__)

    def process_yaml_file(self, yaml_path: Path) -> List[LocalizableEntity]:
        """
        Обрабатывает один YAML-файл и извлекает локализуемые сущности

        Args:
            yaml_path: Путь к YAML-файлу

        Returns:
            Список LocalizableEntity
        """
        try:
            # Загружаем YAML
            yaml_data = self.yaml_handler.load(yaml_path)

            # Фильтруем сущности
            yaml_entities = self.yaml_handler.filter_entities(yaml_data)

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

    def generate_fluent_for_group(
        self,
        yaml_files: List[Path],
        output_path: Path
    ) -> bool:
        """
        Генерирует Fluent-файл для группы YAML-файлов

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
            self.logger.info(f"Нет локализуемых сущностей для {output_path}")
            return False

        # Генерируем Fluent-контент
        fluent_content = self.serializer.entities_to_ast(
            all_entities,
            add_comments=True,
            use_parent_references=False
        )

        # Форматируем
        formatted = self.formatter.format_ast(fluent_content)

        # Создаем директорию если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем
        self.file_handler.write(output_path, formatted)

        self.logger.info(f"Создан {output_path} ({len(all_entities)} сущностей)")
        return True

    def generate_all_locales(self) -> Dict[str, int]:
        """
        Генерирует все Fluent-файлы из YAML-прототипов напрямую в ru-RU

        Returns:
            Статистика {status: count}
        """
        stats = {
            'created_ru': 0,
            'skipped': 0,
            'errors': 0
        }

        # Группируем файлы
        grouped = self.group_yaml_files_by_locale_path()

        self.logger.info(f"Обработка {len(grouped)} групп файлов...")

        for locale_path, yaml_files in grouped.items():
            try:
                # locale_path уже указывает на ru-RU/ss14-ru/...
                # Генерируем Fluent-файл напрямую в ru-RU
                success = self.generate_fluent_for_group(yaml_files, locale_path)

                if success:
                    stats['created_ru'] += 1
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
