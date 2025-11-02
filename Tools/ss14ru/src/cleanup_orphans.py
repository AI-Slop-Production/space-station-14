"""
Утилита для удаления orphan-ключей (ключей, которых больше нет в источниках)
"""

from pathlib import Path
from typing import Dict, Set, List
from fluent.syntax import parse, serialize
from fluent.syntax.ast import Message, Term, Resource
import logging

from .config import ProjectConfig
from .file_handlers import FluentFileHandler
from .fluent_formatter import FluentFormatter
from .yaml_handler import YAMLHandler


class OrphanCleaner:
    """Очистка orphan-ключей из ru-RU локали"""

    def __init__(self, config: ProjectConfig):
        """
        Инициализация очистителя

        Args:
            config: Конфигурация проекта
        """
        self.config = config
        self.file_handler = FluentFileHandler()
        self.formatter = FluentFormatter()
        self.yaml_handler = YAMLHandler()
        self.logger = logging.getLogger(__name__)

    def get_all_entity_ids_from_yaml(self) -> tuple[Set[str], int]:
        """
        Собирает все entity ID из YAML прототипов

        Returns:
            Кортеж (множество entity ID, количество ошибок парсинга)
        """
        entity_ids = set()
        parse_errors = 0

        yaml_files = self.config.get_prototype_files()

        for yaml_file in yaml_files:
            try:
                entities = self.yaml_handler.extract_localizable_entities(yaml_file)
                for entity in entities:
                    if 'id' in entity:
                        entity_ids.add(entity['id'])
            except Exception as e:
                # Если ошибка связана с табуляцией - попробуем исправить
                error_msg = str(e)
                if 'found character' in error_msg and 'cannot start any token' in error_msg:
                    try:
                        # Пробуем прочитать файл и заменить табы на пробелы
                        with open(yaml_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Заменяем табуляцию на 2 пробела (стандарт YAML)
                        fixed_content = content.replace('\t', '  ')

                        # Пробуем распарсить исправленный контент
                        import yaml
                        from io import StringIO

                        data = yaml.safe_load(StringIO(fixed_content))
                        if data is None:
                            data = []
                        if not isinstance(data, list):
                            data = [data]

                        # Извлекаем entity ID из исправленных данных
                        for item in data:
                            if isinstance(item, dict) and item.get('type') == 'entity' and 'id' in item:
                                entity_ids.add(item['id'])

                        parse_errors += 1
                        rel_path = yaml_file.relative_to(self.config.prototypes_dir)
                        self.logger.warning(
                            f"Обработан {rel_path}: Табуляция заменена на пробелы "
                            f"(извлечено {len([i for i in data if isinstance(i, dict) and i.get('type') == 'entity'])} entity)"
                        )
                        continue

                    except Exception as fix_error:
                        # Не удалось исправить - пропускаем
                        parse_errors += 1
                        rel_path = yaml_file.relative_to(self.config.prototypes_dir)
                        self.logger.warning(
                            f"Пропуск {rel_path}: Не удалось обработать после замены табуляции: {fix_error}"
                        )
                        continue

                # Другие типы ошибок
                parse_errors += 1
                rel_path = yaml_file.relative_to(self.config.prototypes_dir)
                self.logger.warning(f"Пропуск {rel_path}: {error_msg}")
                continue

        return entity_ids, parse_errors

    def get_keys_from_en_us_file(self, en_us_path: Path) -> Set[str]:
        """
        Извлекает все ключи из en-US файла

        Args:
            en_us_path: Путь к en-US файлу

        Returns:
            Множество ключей (включая атрибуты как отдельные ключи)
        """
        if not en_us_path.exists():
            return set()

        try:
            content = self.file_handler.read(en_us_path)
            resource = parse(content)

            keys = set()
            for entry in resource.body:
                if isinstance(entry, (Message, Term)):
                    # Добавляем основной ключ
                    keys.add(entry.id.name)

                    # Добавляем атрибуты
                    if entry.attributes:
                        for attr in entry.attributes:
                            # Сохраняем как "key.attribute"
                            keys.add(f"{entry.id.name}.{attr.id.name}")

            return keys
        except Exception as e:
            self.logger.error(f"Ошибка парсинга {en_us_path}: {e}")
            return set()

    def get_ru_ru_path_from_en_us(self, en_us_path: Path) -> Path:
        """
        Конвертирует путь en-US файла в ru-RU путь

        Args:
            en_us_path: Путь к en-US файлу

        Returns:
            Путь к ru-RU файлу
        """
        path_str = str(en_us_path)
        ru_ru_str = path_str.replace('/en-US/', '/ru-RU/').replace('\\en-US\\', '\\ru-RU\\')
        return Path(ru_ru_str)

    def get_en_us_path_from_ru_ru(self, ru_ru_path: Path) -> Path:
        """
        Конвертирует путь ru-RU файла в en-US путь

        Обрабатывает два случая:
        1. Обычные локали: Resources/Locale/ru-RU/foo.ftl -> Resources/Locale/en-US/foo.ftl
        2. RobustToolbox: Resources/Locale/ru-RU/robust-toolbox/foo.ftl -> RobustToolbox/Resources/Locale/en-US/foo.ftl

        Args:
            ru_ru_path: Путь к ru-RU файлу

        Returns:
            Путь к en-US файлу
        """
        # Проверяем, из robust-toolbox ли этот файл
        try:
            relative = ru_ru_path.relative_to(self.config.ru_ru_robust_toolbox)
            # Это файл из RobustToolbox - конвертируем в RobustToolbox/Resources/Locale/en-US/
            return self.config.robust_toolbox_en_us / relative
        except ValueError:
            # Это обычный файл - простая замена ru-RU на en-US
            path_str = str(ru_ru_path)
            en_us_str = path_str.replace('/ru-RU/', '/en-US/').replace('\\ru-RU\\', '\\en-US\\')
            return Path(en_us_str)

    def is_ss14_ru_generated_file(self, ru_ru_path: Path) -> bool:
        """
        Проверяет, является ли файл сгенерированным из YAML (в папке ss14-ru/)

        Args:
            ru_ru_path: Путь к ru-RU файлу

        Returns:
            True если файл в ss14-ru/
        """
        return 'ss14-ru' in ru_ru_path.parts or '/ss14-ru/' in str(ru_ru_path) or '\\ss14-ru\\' in str(ru_ru_path)

    def clean_orphan_keys_from_file(
        self,
        ru_ru_path: Path,
        valid_keys: Set[str],
        dry_run: bool = False
    ) -> int:
        """
        Удаляет orphan-ключи из файла

        Args:
            ru_ru_path: Путь к ru-RU файлу
            valid_keys: Множество валидных ключей (которые должны остаться)
            dry_run: Режим предпросмотра

        Returns:
            Количество удаленных ключей
        """
        if not ru_ru_path.exists():
            return 0

        try:
            content = self.file_handler.read(ru_ru_path)
            resource = parse(content)

            new_body = []
            removed_count = 0

            for entry in resource.body:
                if isinstance(entry, (Message, Term)):
                    key = entry.id.name

                    # Проверяем основной ключ
                    if key in valid_keys:
                        # Проверяем атрибуты
                        if entry.attributes:
                            valid_attrs = []
                            for attr in entry.attributes:
                                attr_full_key = f"{key}.{attr.id.name}"
                                if attr_full_key in valid_keys:
                                    valid_attrs.append(attr)
                                else:
                                    removed_count += 1
                                    if dry_run:
                                        self.logger.info(f"  [DRY RUN] Удален атрибут: {attr_full_key}")

                            # Обновляем атрибуты
                            entry.attributes = valid_attrs if valid_attrs else None

                        new_body.append(entry)
                    else:
                        removed_count += 1
                        if dry_run:
                            self.logger.info(f"  [DRY RUN] Удален ключ: {key}")
                else:
                    # Сохраняем комментарии и прочее
                    new_body.append(entry)

            if removed_count > 0 and not dry_run:
                resource.body = new_body
                formatted = self.formatter.format_ast(resource)
                self.file_handler.write(ru_ru_path, formatted)

                rel_path = ru_ru_path.relative_to(self.config.locale_dir)
                self.logger.info(f"Очищен {rel_path}: удалено {removed_count} orphan-ключей")

            return removed_count

        except Exception as e:
            self.logger.error(f"Ошибка очистки {ru_ru_path}: {e}")
            return 0

    def clean_ss14_ru_files(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Очищает файлы ss14-ru/ от ключей, которых нет в YAML прототипах

        Args:
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        stats = {
            'files_processed': 0,
            'files_cleaned': 0,
            'orphans_removed': 0,
            'yaml_parse_errors': 0,
            'errors': 0
        }

        # Собираем все entity ID из YAML
        self.logger.info("Сканирование YAML прототипов...")
        valid_entity_ids, yaml_errors = self.get_all_entity_ids_from_yaml()
        stats['yaml_parse_errors'] = yaml_errors

        self.logger.info(f"Найдено {len(valid_entity_ids)} entity в YAML прототипах")
        if yaml_errors > 0:
            self.logger.warning(f"Пропущено {yaml_errors} YAML файлов с ошибками парсинга")

        # Формируем валидные ключи (с префиксом ent-)
        valid_keys = set()
        for entity_id in valid_entity_ids:
            valid_keys.add(f"ent-{entity_id}")
            valid_keys.add(f"ent-{entity_id}.desc")
            valid_keys.add(f"ent-{entity_id}.suffix")

        # Находим все ss14-ru файлы
        ss14_ru_dir = self.config.ru_ru_locale / "ss14-ru"
        if not ss14_ru_dir.exists():
            return stats

        ftl_files = list(ss14_ru_dir.rglob("*.ftl"))

        for ftl_file in ftl_files:
            stats['files_processed'] += 1

            try:
                removed = self.clean_orphan_keys_from_file(ftl_file, valid_keys, dry_run)

                if removed > 0:
                    stats['files_cleaned'] += 1
                    stats['orphans_removed'] += removed

            except Exception as e:
                self.logger.error(f"Ошибка обработки {ftl_file}: {e}")
                stats['errors'] += 1

        return stats

    def clean_regular_locale_files(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Очищает обычные файлы локали (не ss14-ru) на основе en-US

        Args:
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        stats = {
            'files_processed': 0,
            'files_cleaned': 0,
            'files_deleted': 0,  # Файлы удаленные полностью (нет en-US)
            'orphans_removed': 0,
            'errors': 0
        }

        # Находим все ru-RU файлы (кроме ss14-ru)
        ru_ru_dir = self.config.ru_ru_locale
        if not ru_ru_dir.exists():
            return stats

        ftl_files = [f for f in ru_ru_dir.rglob("*.ftl") if not self.is_ss14_ru_generated_file(f)]

        for ru_ru_file in ftl_files:
            stats['files_processed'] += 1

            try:
                # Находим соответствующий en-US файл
                en_us_file = self.get_en_us_path_from_ru_ru(ru_ru_file)

                if not en_us_file.exists():
                    # Если нет en-US файла - удаляем ru-RU файл полностью
                    rel_path = ru_ru_file.relative_to(self.config.locale_dir)

                    if dry_run:
                        self.logger.info(f"[DRY RUN] Будет удален orphan файл (нет en-US): {rel_path}")
                    else:
                        ru_ru_file.unlink()
                        self.logger.info(f"Удален orphan файл (нет en-US): {rel_path}")

                    stats['files_deleted'] += 1
                    continue

                # Получаем валидные ключи из en-US
                valid_keys = self.get_keys_from_en_us_file(en_us_file)

                if not valid_keys:
                    continue

                # Удаляем orphan-ключи
                removed = self.clean_orphan_keys_from_file(ru_ru_file, valid_keys, dry_run)

                if removed > 0:
                    stats['files_cleaned'] += 1
                    stats['orphans_removed'] += removed

            except Exception as e:
                self.logger.error(f"Ошибка обработки {ru_ru_file}: {e}")
                stats['errors'] += 1

        return stats

    def clean_all(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Очищает все orphan-ключи из ru-RU локали

        Args:
            dry_run: Режим предпросмотра

        Returns:
            Общая статистика
        """
        if dry_run:
            self.logger.info("[DRY RUN MODE] Предпросмотр удаления orphan-ключей:")

        # Очищаем ss14-ru файлы
        self.logger.info("\nОчистка ss14-ru файлов (на основе YAML прототипов)...")
        ss14_stats = self.clean_ss14_ru_files(dry_run)

        # Очищаем обычные файлы
        self.logger.info("\nОчистка обычных файлов локали (на основе en-US)...")
        regular_stats = self.clean_regular_locale_files(dry_run)

        # Объединяем статистику
        total_stats = {
            'files_processed': ss14_stats['files_processed'] + regular_stats['files_processed'],
            'files_cleaned': ss14_stats['files_cleaned'] + regular_stats['files_cleaned'],
            'files_deleted': regular_stats.get('files_deleted', 0),  # Только regular files могут быть удалены
            'orphans_removed': ss14_stats['orphans_removed'] + regular_stats['orphans_removed'],
            'yaml_parse_errors': ss14_stats.get('yaml_parse_errors', 0),
            'errors': ss14_stats['errors'] + regular_stats['errors']
        }

        return total_stats
