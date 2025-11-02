"""
Синхронизация локалей между en-US и ru-RU
"""

from pathlib import Path
from typing import List, Dict, Set, Tuple
from fluent.syntax import parse
from fluent.syntax.ast import Message, Term, Resource
import logging

from .config import ProjectConfig
from .file_handlers import FluentFileHandler
from .fluent_formatter import FluentFormatter


class LocaleSync:
    """Синхронизатор локалей en-US -> ru-RU"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация синхронизатора

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.file_handler = FluentFileHandler()
        self.formatter = FluentFormatter()
        self.logger = logging.getLogger(__name__)

    def get_file_pairs(self) -> List[Tuple[Path, Path]]:
        """
        Получает пары файлов (en-US, ru-RU) для синхронизации

        Включает файлы из двух источников:
        1. Resources/Locale/en-US -> Resources/Locale/ru-RU
        2. RobustToolbox/Resources/Locale/en-US -> Resources/Locale/ru-RU/robust-toolbox

        Returns:
            Список кортежей (en_path, ru_path)
        """
        pairs = []

        # Обычные файлы из Resources/Locale/en-US
        en_files = self.config.get_fluent_files(self.config.en_us_locale)
        for en_file in en_files:
            ru_file = self.config.get_mirrored_locale_path(en_file)
            pairs.append((en_file, ru_file))

        # Файлы из RobustToolbox (если директория существует)
        if self.config.robust_toolbox_en_us.exists():
            rt_files = self.config.get_fluent_files(self.config.robust_toolbox_en_us)
            for en_file in rt_files:
                ru_file = self.config.get_mirrored_locale_path(en_file)
                pairs.append((en_file, ru_file))
        else:
            self.logger.debug("RobustToolbox en-US locale не найдена, пропускаем")

        return pairs

    def extract_keys_from_ast(self, resource: Resource) -> Dict[str, Set[str]]:
        """
        Извлекает ключи и атрибуты из Fluent AST

        Обрабатывает как Messages (обычные сообщения), так и Terms (термины с префиксом -)

        Args:
            resource: Fluent AST Resource

        Returns:
            Словарь {message_key: {attribute1, attribute2, ...}}
        """
        keys = {}

        for entry in resource.body:
            # Обрабатываем как Messages, так и Terms
            if isinstance(entry, (Message, Term)):
                message_key = entry.id.name
                attributes = set()

                if entry.attributes:
                    for attr in entry.attributes:
                        attributes.add(attr.id.name)

                keys[message_key] = attributes

        return keys

    def sync_file_pair(
        self,
        en_path: Path,
        ru_path: Path,
        create_missing: bool = True,
        warn_orphans: bool = True
    ) -> Dict[str, int]:
        """
        Синхронизирует пару файлов

        Args:
            en_path: Путь к английскому файлу
            ru_path: Путь к русскому файлу
            create_missing: Создавать ли отсутствующий русский файл
            warn_orphans: Предупреждать ли об orphan-ключах

        Returns:
            Статистика изменений
        """
        stats = {
            'keys_added': 0,
            'attributes_added': 0,
            'orphan_keys': 0,
            'created': 0
        }

        # Проверяем существование английского файла
        if not en_path.exists():
            self.logger.warning(f"Английский файл не существует: {en_path}")
            return stats

        # Парсим английский файл
        en_content = self.file_handler.read(en_path)
        en_resource = parse(en_content)
        en_keys = self.extract_keys_from_ast(en_resource)

        # Если русский файл не существует
        if not ru_path.exists():
            if create_missing:
                # Создаем русский файл как копию английского
                ru_path.parent.mkdir(parents=True, exist_ok=True)
                self.file_handler.write(ru_path, en_content)
                stats['created'] = 1
                self.logger.info(f"Создан русский файл: {ru_path}")
            return stats

        # Парсим русский файл
        ru_content = self.file_handler.read(ru_path)
        ru_resource = parse(ru_content)
        ru_keys = self.extract_keys_from_ast(ru_resource)

        # Находим отсутствующие ключи и атрибуты
        missing_keys = set(en_keys.keys()) - set(ru_keys.keys())
        orphan_keys = set(ru_keys.keys()) - set(en_keys.keys())

        # Предупреждаем об orphan-ключах
        if warn_orphans and orphan_keys:
            stats['orphan_keys'] = len(orphan_keys)
            self.logger.warning(
                f"Orphan-ключи в {ru_path}: {', '.join(sorted(orphan_keys))}"
            )

        # Добавляем отсутствующие ключи
        if missing_keys or self._has_missing_attributes(en_keys, ru_keys):
            # Копируем недостающие сообщения из английского в русский
            modified = self._merge_resources(en_resource, ru_resource, en_keys, ru_keys)

            if modified:
                # Форматируем и сохраняем
                formatted = self.formatter.format_ast(ru_resource)
                self.file_handler.write(ru_path, formatted)

                stats['keys_added'] = len(missing_keys)
                # Подсчитываем добавленные атрибуты
                for key in en_keys:
                    if key in ru_keys:
                        missing_attrs = en_keys[key] - ru_keys[key]
                        stats['attributes_added'] += len(missing_attrs)

                self.logger.info(
                    f"Обновлен {ru_path}: "
                    f"+{stats['keys_added']} ключей, "
                    f"+{stats['attributes_added']} атрибутов"
                )

        return stats

    def _has_missing_attributes(
        self,
        en_keys: Dict[str, Set[str]],
        ru_keys: Dict[str, Set[str]]
    ) -> bool:
        """Проверяет наличие недостающих атрибутов"""
        for key in en_keys:
            if key in ru_keys:
                if en_keys[key] - ru_keys[key]:
                    return True
        return False

    def _merge_resources(
        self,
        en_resource: Resource,
        ru_resource: Resource,
        en_keys: Dict[str, Set[str]],
        ru_keys: Dict[str, Set[str]]
    ) -> bool:
        """
        Объединяет ресурсы, добавляя недостающие ключи и атрибуты

        Обрабатывает как Messages, так и Terms

        Returns:
            True если были изменения
        """
        modified = False
        # Собираем все русские записи (Messages и Terms) по ключам
        ru_entries = {
            entry.id.name: entry
            for entry in ru_resource.body
            if isinstance(entry, (Message, Term))
        }

        # Проходим по всем английским записям (Messages и Terms)
        for entry in en_resource.body:
            if not isinstance(entry, (Message, Term)):
                continue

            msg_key = entry.id.name

            # Если ключа вообще нет в русском
            if msg_key not in ru_keys:
                # Добавляем запись в конец
                ru_resource.body.append(entry)
                modified = True
            else:
                # Проверяем атрибуты
                missing_attrs = en_keys[msg_key] - ru_keys[msg_key]
                if missing_attrs:
                    # Добавляем недостающие атрибуты
                    ru_entry = ru_entries[msg_key]
                    if ru_entry.attributes is None:
                        ru_entry.attributes = []

                    for en_attr in entry.attributes or []:
                        if en_attr.id.name in missing_attrs:
                            ru_entry.attributes.append(en_attr)
                            modified = True

        return modified

    def sync_all(
        self,
        create_missing: bool = True,
        warn_orphans: bool = True
    ) -> Dict[str, int]:
        """
        Синхронизирует все файлы локалей

        Args:
            create_missing: Создавать ли отсутствующие русские файлы
            warn_orphans: Предупреждать ли об orphan-ключах

        Returns:
            Общая статистика
        """
        total_stats = {
            'files_processed': 0,
            'files_created': 0,
            'total_keys_added': 0,
            'total_attributes_added': 0,
            'total_orphans': 0,
            'errors': 0
        }

        pairs = self.get_file_pairs()
        self.logger.info(f"Синхронизация {len(pairs)} файлов...")

        for en_path, ru_path in pairs:
            try:
                stats = self.sync_file_pair(
                    en_path,
                    ru_path,
                    create_missing=create_missing,
                    warn_orphans=warn_orphans
                )

                total_stats['files_processed'] += 1
                total_stats['files_created'] += stats.get('created', 0)
                total_stats['total_keys_added'] += stats.get('keys_added', 0)
                total_stats['total_attributes_added'] += stats.get('attributes_added', 0)
                total_stats['total_orphans'] += stats.get('orphan_keys', 0)

            except Exception as e:
                self.logger.error(f"Ошибка синхронизации {en_path}: {e}")
                total_stats['errors'] += 1

        return total_stats
