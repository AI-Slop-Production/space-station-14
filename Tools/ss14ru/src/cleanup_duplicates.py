"""
Утилита для удаления дублирующихся блоков сущностей в Fluent-файлах.
Находит дубликаты МЕЖДУ РАЗНЫМИ ФАЙЛАМИ и оставляет ключ только в том файле,
который соответствует en-US локализации.
"""

from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from fluent.syntax import parse, serialize
from fluent.syntax.ast import Message, Resource, Comment, Term
import logging

from .config import ProjectConfig
from .file_handlers import FluentFileHandler
from .fluent_formatter import FluentFormatter


class DuplicateCleaner:
    """Очистка дублирующихся сообщений в Fluent-файлах между разными файлами"""

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

    def get_en_us_path(self, ru_ru_path: Path) -> Path:
        """
        Конвертирует путь ru-RU файла в соответствующий en-US путь

        Args:
            ru_ru_path: Путь к файлу в ru-RU

        Returns:
            Путь к соответствующему файлу в en-US
        """
        # Заменяем ru-RU на en-US в пути
        path_str = str(ru_ru_path)
        en_us_str = path_str.replace('/ru-RU/', '/en-US/').replace('\\ru-RU\\', '\\en-US\\')
        return Path(en_us_str)

    def find_key_in_file(self, file_path: Path, key: str) -> bool:
        """
        Проверяет, существует ли ключ в указанном файле

        Args:
            file_path: Путь к файлу
            key: Ключ для поиска

        Returns:
            True если ключ найден в файле
        """
        if not file_path.exists():
            return False

        try:
            content = self.file_handler.read(file_path)
            resource = parse(content)

            for entry in resource.body:
                if isinstance(entry, (Message, Term)):
                    if entry.id.name == key:
                        return True
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при поиске ключа {key} в {file_path}: {e}")
            return False

    def find_cross_file_duplicates(self, locale_dir: Path) -> Dict[str, List[Path]]:
        """
        Находит дубликаты МЕЖДУ РАЗНЫМИ ФАЙЛАМИ

        Args:
            locale_dir: Директория локали (обычно ru-RU)

        Returns:
            Словарь {ключ: [список файлов где встречается]}
        """
        key_to_files: Dict[str, List[Path]] = {}

        ftl_files = self.config.get_fluent_files(locale_dir)

        for ftl_file in ftl_files:
            try:
                content = self.file_handler.read(ftl_file)
                resource = parse(content)

                for entry in resource.body:
                    if isinstance(entry, (Message, Term)):
                        key = entry.id.name
                        if key not in key_to_files:
                            key_to_files[key] = []
                        key_to_files[key].append(ftl_file)

            except Exception as e:
                self.logger.error(f"Ошибка при сканировании {ftl_file}: {e}")
                continue

        # Оставляем только дубликаты (где больше одного файла)
        duplicates = {k: v for k, v in key_to_files.items() if len(v) > 1}

        return duplicates

    def resolve_duplicate_location(
        self,
        key: str,
        ru_files: List[Path]
    ) -> Optional[Path]:
        """
        Определяет, в каком файле должен остаться ключ на основе en-US

        Args:
            key: Дублирующийся ключ
            ru_files: Список ru-RU файлов где встречается ключ

        Returns:
            Путь к файлу где должен остаться ключ, или None если оставить первый
        """
        # Проверяем каждый ru-RU файл - есть ли соответствующий en-US файл с этим ключом
        for ru_file in ru_files:
            en_us_file = self.get_en_us_path(ru_file)
            if self.find_key_in_file(en_us_file, key):
                return ru_file

        # Если ни в одном en-US файле не нашли - оставляем в первом файле
        return ru_files[0] if ru_files else None

    def remove_key_from_file(self, file_path: Path, key: str) -> bool:
        """
        Удаляет указанный ключ из файла

        Args:
            file_path: Путь к файлу
            key: Ключ для удаления

        Returns:
            True если ключ был удален
        """
        if not file_path.exists():
            return False

        try:
            content = self.file_handler.read(file_path)
            resource = parse(content)

            new_body = []
            removed = False
            skip_next_comment = False

            for i, entry in enumerate(resource.body):
                # Если это Message/Term с нужным ключом - пропускаем
                if isinstance(entry, (Message, Term)) and entry.id.name == key:
                    removed = True
                    # Также удаляем предшествующий комментарий если есть
                    if new_body and isinstance(new_body[-1], Comment):
                        new_body.pop()
                    continue

                new_body.append(entry)

            if removed:
                resource.body = new_body
                formatted = self.formatter.format_ast(resource)
                self.file_handler.write(file_path, formatted)
                return True

            return False

        except Exception as e:
            self.logger.error(f"Ошибка при удалении ключа {key} из {file_path}: {e}")
            return False

    def clean_all(
        self,
        locale_dir: Path = None,
        keep_first: bool = True,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Очищает дубликаты МЕЖДУ РАЗНЫМИ ФАЙЛАМИ на основе en-US локали

        Args:
            locale_dir: Директория локали (по умолчанию ru-RU)
            keep_first: Сохранять первое вхождение (используется как fallback)
            dry_run: Режим предпросмотра

        Returns:
            Статистика
        """
        if locale_dir is None:
            locale_dir = self.config.ru_ru_locale

        stats = {
            'files_processed': 0,
            'duplicate_keys_found': 0,
            'duplicates_removed': 0,
            'errors': 0
        }

        if dry_run:
            self.logger.info("[DRY RUN MODE] Предпросмотр удаления дубликатов:")

        # Находим все дубликаты между файлами
        self.logger.info("Сканирование файлов на наличие дубликатов...")
        duplicates = self.find_cross_file_duplicates(locale_dir)

        if not duplicates:
            self.logger.info("Дубликаты между файлами не найдены")
            return stats

        stats['duplicate_keys_found'] = len(duplicates)
        self.logger.info(f"Найдено дублирующихся ключей: {len(duplicates)}")

        # Обрабатываем каждый дубликат
        for key, files in duplicates.items():
            try:
                # Определяем правильный файл на основе en-US
                correct_file = self.resolve_duplicate_location(key, files)

                if correct_file is None:
                    self.logger.warning(f"Не удалось определить правильное расположение для {key}")
                    continue

                # Относительные пути для логирования
                rel_correct = correct_file.relative_to(self.config.locale_dir)
                rel_files = [f.relative_to(self.config.locale_dir) for f in files]

                if dry_run:
                    self.logger.info(f"\nКлюч: {key}")
                    self.logger.info(f"  Найден в файлах: {[str(f) for f in rel_files]}")
                    self.logger.info(f"  Будет оставлен в: {rel_correct}")
                    files_to_remove = [f for f in files if f != correct_file]
                    if files_to_remove:
                        rel_remove = [f.relative_to(self.config.locale_dir) for f in files_to_remove]
                        self.logger.info(f"  Будет удален из: {[str(f) for f in rel_remove]}")
                else:
                    # Удаляем ключ из всех файлов кроме правильного
                    removed_count = 0
                    for file in files:
                        if file != correct_file:
                            if self.remove_key_from_file(file, key):
                                removed_count += 1
                                stats['files_processed'] += 1
                                rel_file = file.relative_to(self.config.locale_dir)
                                self.logger.info(f"Удален {key} из [{rel_file}]")

                    stats['duplicates_removed'] += removed_count

            except Exception as e:
                self.logger.error(f"Ошибка обработки дубликата {key}: {e}")
                stats['errors'] += 1

        return stats
