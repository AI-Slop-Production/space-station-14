#!/usr/bin/env python3
"""
Главный скрипт для запуска SS14RU Fluent Localization Utility
"""

import sys
import argparse
import logging
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import get_config
from src.yaml_processor import YAMLProcessor, setup_logging
from src.locale_sync import LocaleSync
from src.cleanup_duplicates import DuplicateCleaner
from src.cleanup_empty import EmptyCleaner
from src.cleanup_orphans import OrphanCleaner
from src.normalize_dashes import DashNormalizer


def install_dependencies():
    """Устанавливает зависимости из requirements.txt"""
    import subprocess

    requirements_file = Path(__file__).parent / "requirements.txt"

    print("Установка зависимостей...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("Зависимости успешно установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка установки зависимостей: {e}")
        return False


def generate_from_yaml(config, args):
    """Этап 1: Генерация или обновление Fluent из YAML-прототипов"""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("ЭТАП 1: Генерация локализации из YAML-прототипов")
    logger.info("=" * 60)

    force_overwrite = getattr(args, 'force', False)

    if force_overwrite:
        logger.warning("⚠️  РЕЖИМ ПОЛНОЙ ПЕРЕЗАПИСИ (--force)")
        logger.warning("⚠️  Все существующие файлы будут ПЕРЕЗАПИСАНЫ!")

    processor = YAMLProcessor(config, force_overwrite=force_overwrite)
    stats = processor.generate_all_locales()

    logger.info("\nРезультаты генерации:")
    logger.info(f"  Создано файлов: {stats['created']}")
    logger.info(f"  Обновлено файлов: {stats['updated']}")
    logger.info(f"  Без изменений: {stats['unchanged']}")
    logger.info(f"  Пропущено: {stats['skipped']}")
    logger.info(f"  Ошибок: {stats['errors']}")

    return stats['errors'] == 0


def sync_locales(config, args):
    """Этап 2: Синхронизация локалей en-US -> ru-RU"""
    logger = logging.getLogger(__name__)
    logger.info("\n" + "=" * 60)
    logger.info("ЭТАП 2: Синхронизация локалей en-US -> ru-RU")
    logger.info("=" * 60)

    syncer = LocaleSync(config)
    stats = syncer.sync_all(
        create_missing=not args.no_create,
        warn_orphans=not args.no_warnings
    )

    logger.info("\nРезультаты синхронизации:")
    logger.info(f"  Обработано файлов: {stats['files_processed']}")
    logger.info(f"  Создано файлов: {stats['files_created']}")
    logger.info(f"  Добавлено ключей: {stats['total_keys_added']}")
    logger.info(f"  Добавлено атрибутов: {stats['total_attributes_added']}")
    logger.info(f"  Orphan-ключей: {stats['total_orphans']}")
    logger.info(f"  Ошибок: {stats['errors']}")

    return stats['errors'] == 0


def cleanup_duplicates(config, args):
    """Этап 3: Очистка дубликатов"""
    logger = logging.getLogger(__name__)
    logger.info("\n" + "=" * 60)
    logger.info("ЭТАП 3: Очистка дублирующихся ключей")
    logger.info("=" * 60)

    cleaner = DuplicateCleaner(config)
    stats = cleaner.clean_all(
        locale_dir=config.ru_ru_locale,
        keep_first=True,
        dry_run=args.dry_run
    )

    logger.info("\nРезультаты очистки дубликатов:")
    logger.info(f"  Найдено дублирующихся ключей: {stats['duplicate_keys_found']}")
    logger.info(f"  Удалено дубликатов: {stats['duplicates_removed']}")
    logger.info(f"  Обработано файлов: {stats['files_processed']}")
    logger.info(f"  Ошибок: {stats['errors']}")

    return stats['errors'] == 0


def cleanup_empty(config, args):
    """Этап 4: Очистка пустых файлов"""
    logger = logging.getLogger(__name__)
    logger.info("\n" + "=" * 60)
    logger.info("ЭТАП 4: Очистка пустых файлов и директорий")
    logger.info("=" * 60)

    cleaner = EmptyCleaner(config)
    stats = cleaner.clean_all(
        locale_dir=config.ru_ru_locale,
        dry_run=args.dry_run
    )

    logger.info("\nРезультаты очистки:")
    logger.info(f"  Удалено файлов: {stats['files_deleted']}")
    logger.info(f"  Удалено директорий: {stats['dirs_deleted']}")
    logger.info(f"  Ошибок: {stats['errors']}")

    return stats['errors'] == 0


def cleanup_orphans(config, args):
    """Этап 5: Очистка orphan-ключей"""
    logger = logging.getLogger(__name__)
    logger.info("\n" + "=" * 60)
    logger.info("ЭТАП 5: Очистка orphan-ключей")
    logger.info("=" * 60)

    cleaner = OrphanCleaner(config)
    stats = cleaner.clean_all(dry_run=args.dry_run)

    logger.info("\nРезультаты очистки orphan-ключей:")
    logger.info(f"  Обработано файлов: {stats['files_processed']}")
    logger.info(f"  Очищено файлов: {stats['files_cleaned']}")
    logger.info(f"  Удалено orphan-ключей: {stats['orphans_removed']}")
    if stats.get('yaml_parse_errors', 0) > 0:
        logger.info(f"  Пропущено YAML файлов с ошибками: {stats['yaml_parse_errors']}")
    logger.info(f"  Ошибок: {stats['errors']}")

    return stats['errors'] == 0


def normalize_dashes(config, args):
    """Этап 6: Нормализация тире (опционально)"""
    if args.skip_normalize:
        return True

    logger = logging.getLogger(__name__)
    logger.info("\n" + "=" * 60)
    logger.info("ЭТАП 5: Нормализация тире")
    logger.info("=" * 60)

    normalizer = DashNormalizer(config)
    stats = normalizer.normalize_all(
        locale_dir=config.ru_ru_locale,
        dry_run=args.dry_run
    )

    logger.info("\nРезультаты нормализации:")
    logger.info(f"  Обработано файлов: {stats['files_processed']}")
    logger.info(f"  Изменено файлов: {stats['files_modified']}")
    logger.info(f"  Всего замен: {stats['total_replacements']}")
    logger.info(f"  Ошибок: {stats['errors']}")

    return stats['errors'] == 0


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description="SS14RU Fluent Localization Utility - автоматизация работы с локализацией"
    )

    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Установить зависимости перед запуском"
    )

    parser.add_argument(
        "--step",
        choices=["generate", "sync", "cleanup-dupes", "cleanup-empty", "cleanup-orphans", "normalize", "all"],
        default="all",
        help="Выполнить конкретный этап (по умолчанию: all)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Режим предпросмотра (не вносить изменения)"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="⚠️  ОПАСНО: Полная перезапись существующих файлов локализации (удаляет все переводы!)"
    )

    parser.add_argument(
        "--no-create",
        action="store_true",
        help="Не создавать отсутствующие русские файлы при синхронизации"
    )

    parser.add_argument(
        "--no-warnings",
        action="store_true",
        help="Не выводить предупреждения об orphan-ключах"
    )

    parser.add_argument(
        "--skip-normalize",
        action="store_true",
        help="Пропустить этап нормализации тире"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод"
    )

    args = parser.parse_args()

    # Настраиваем логирование
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Устанавливаем зависимости если нужно
    if args.install_deps:
        if not install_dependencies():
            return 1

    try:
        # Получаем конфигурацию
        logger.info("Инициализация конфигурации проекта...")
        config = get_config()
        logger.info(f"Корень проекта: {config.project_root}")
        logger.info(f"Директория прототипов: {config.prototypes_dir}")
        logger.info(f"Целевая локаль: {config.ru_ru_locale}")

        # Создаем необходимые директории
        config.ensure_directories()

        # Выполняем этапы
        success = True

        if args.step in ["generate", "all"]:
            success = generate_from_yaml(config, args) and success

        if args.step in ["sync", "all"]:
            success = sync_locales(config, args) and success

        if args.step in ["cleanup-dupes", "all"]:
            success = cleanup_duplicates(config, args) and success

        if args.step in ["cleanup-empty", "all"]:
            success = cleanup_empty(config, args) and success

        if args.step in ["cleanup-orphans", "all"]:
            success = cleanup_orphans(config, args) and success

        if args.step in ["normalize", "all"]:
            success = normalize_dashes(config, args) and success

        # Итоговый статус
        logger.info("\n" + "=" * 60)
        if success:
            logger.info("ВСЕ ЭТАПЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        else:
            logger.warning("НЕКОТОРЫЕ ЭТАПЫ ЗАВЕРШЕНЫ С ОШИБКАМИ")
        logger.info("=" * 60)

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
