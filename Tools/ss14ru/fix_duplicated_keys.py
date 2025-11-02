#!/usr/bin/env python3
"""
Скрипт для исправления дублированных ключей в Fluent файлах.

Исправляет паттерн:
    ent-SomeId = ent-SomeId = actual value
→
    ent-SomeId = actual value

Использование:
    python fix_duplicated_keys.py [--dry-run] [--path PATH]
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple
import argparse

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from src.file_handlers import FluentFileHandler


class KeyDuplicationFixer:
    """Исправляет дублированные ключи в Fluent файлах"""

    def __init__(self):
        self.file_handler = FluentFileHandler()
        # Паттерн для поиска дублированных ключей:
        # Ищем: "ent-Something = ent-Something = value"
        # Группа 1: ключ (ent-Something)
        # Группа 2: всё остальное после второго знака равно
        self.pattern = re.compile(
            r'^(ent-[A-Za-z0-9_-]+)\s*=\s*\1\s*=\s*(.+)$',
            re.MULTILINE
        )

    def check_file(self, file_path: Path) -> List[Tuple[str, str, str]]:
        """
        Проверяет файл на наличие дублированных ключей

        Args:
            file_path: Путь к файлу

        Returns:
            Список кортежей (full_match, key, correct_value)
        """
        content = self.file_handler.read(file_path)
        matches = []

        for match in self.pattern.finditer(content):
            full_match = match.group(0)
            key = match.group(1)
            value = match.group(2)
            matches.append((full_match, key, value))

        return matches

    def fix_file(self, file_path: Path, dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        Исправляет дублированные ключи в файле

        Args:
            file_path: Путь к файлу
            dry_run: Режим предпросмотра (не сохранять изменения)

        Returns:
            Кортеж (количество исправлений, список исправленных ключей)
        """
        content = self.file_handler.read(file_path)
        fixed_keys = []

        def replace_func(match):
            key = match.group(1)
            value = match.group(2)
            fixed_keys.append(key)
            return f"{key} = {value}"

        new_content = self.pattern.sub(replace_func, content)

        # Если есть изменения и не dry-run - сохраняем
        if new_content != content and not dry_run:
            self.file_handler.write(file_path, new_content)

        return len(fixed_keys), fixed_keys

    def process_directory(
        self,
        directory: Path,
        dry_run: bool = False,
        verbose: bool = False
    ) -> Tuple[int, int, int]:
        """
        Обрабатывает все .ftl файлы в директории

        Args:
            directory: Директория для обработки
            dry_run: Режим предпросмотра
            verbose: Подробный вывод

        Returns:
            Кортеж (всего файлов, файлов с ошибками, всего исправлений)
        """
        ftl_files = list(directory.rglob("*.ftl"))

        total_files = 0
        files_with_errors = 0
        total_fixes = 0

        for ftl_file in ftl_files:
            total_files += 1

            try:
                count, fixed_keys = self.fix_file(ftl_file, dry_run=dry_run)

                if count > 0:
                    files_with_errors += 1
                    total_fixes += count

                    rel_path = ftl_file.relative_to(directory)

                    if dry_run:
                        print(f"[DRY RUN] {rel_path}: {count} дублированных ключей")
                    else:
                        print(f"[FIXED] {rel_path}: {count} исправлений")

                    if verbose:
                        for key in fixed_keys:
                            print(f"  - {key}")

            except Exception as e:
                print(f"[ERROR] {ftl_file}: {e}")

        return total_files, files_with_errors, total_fixes


def main():
    parser = argparse.ArgumentParser(
        description="Исправляет дублированные ключи в Fluent файлах"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим предпросмотра (не сохранять изменения)'
    )
    parser.add_argument(
        '--path',
        type=str,
        default=None,
        help='Путь к директории или файлу (по умолчанию: Resources/Locale/ru-RU)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Подробный вывод (показывать все исправленные ключи)'
    )

    args = parser.parse_args()

    # Определяем путь
    if args.path:
        target_path = Path(args.path)
    else:
        # По умолчанию - ru-RU в корне проекта
        script_dir = Path(__file__).parent
        project_root = script_dir.parent.parent
        target_path = project_root / "Resources" / "Locale" / "ru-RU"

    if not target_path.exists():
        print(f"ERROR: Путь не существует: {target_path}")
        sys.exit(1)

    fixer = KeyDuplicationFixer()

    print("=" * 60)
    print("Исправление дублированных ключей в Fluent файлах")
    print("=" * 60)

    if args.dry_run:
        print("[DRY RUN MODE] Изменения не будут сохранены\n")

    # Обрабатываем файл или директорию
    total_fixes = 0

    if target_path.is_file():
        print(f"Обработка файла: {target_path}\n")
        count, fixed_keys = fixer.fix_file(target_path, dry_run=args.dry_run)
        total_fixes = count

        if count > 0:
            if args.dry_run:
                print(f"Найдено дублированных ключей: {count}")
            else:
                print(f"Исправлено ключей: {count}")

            if args.verbose:
                print("\nИсправленные ключи:")
                for key in fixed_keys:
                    print(f"  - {key}")
        else:
            print("Дублированные ключи не найдены")

    else:
        print(f"Обработка директории: {target_path}\n")
        total_files, files_with_errors, total_fixes = fixer.process_directory(
            target_path,
            dry_run=args.dry_run,
            verbose=args.verbose
        )

        print("\n" + "=" * 60)
        print("Результаты:")
        print(f"  Всего файлов: {total_files}")
        print(f"  Файлов с ошибками: {files_with_errors}")
        print(f"  Всего исправлений: {total_fixes}")
        print("=" * 60)

    if args.dry_run and total_fixes > 0:
        print("\nЗапустите без --dry-run чтобы применить исправления")


if __name__ == "__main__":
    main()
