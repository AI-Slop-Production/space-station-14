"""
Обработчики для чтения и записи файлов
"""

from pathlib import Path
from typing import Optional
from fluent.syntax import parse, serialize
from fluent.syntax.ast import Resource, Junk


class TextFileHandler:
    """Базовый обработчик для текстовых файлов"""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Инициализация обработчика

        Args:
            base_path: Базовый путь для относительных путей
        """
        self.base_path = base_path or Path.cwd()

    def read(self, file_path: Path, relative: bool = False) -> str:
        """
        Читает текстовый файл

        Args:
            file_path: Путь к файлу
            relative: Использовать ли относительный путь от base_path

        Returns:
            Содержимое файла
        """
        if relative:
            file_path = self.base_path / file_path

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write(self, file_path: Path, content: str, relative: bool = False):
        """
        Записывает текстовый файл

        Args:
            file_path: Путь к файлу
            content: Содержимое для записи
            relative: Использовать ли относительный путь от base_path
        """
        if relative:
            file_path = self.base_path / file_path

        # Создаем директории, если их нет
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)


class FluentFileHandler(TextFileHandler):
    """Специализированный обработчик для Fluent-файлов"""

    def read(self, file_path: Path, relative: bool = False) -> str:
        """
        Читает Fluent-файл, удаляя BOM если присутствует

        Args:
            file_path: Путь к файлу
            relative: Использовать ли относительный путь от base_path

        Returns:
            Содержимое файла без BOM
        """
        content = super().read(file_path, relative)

        # Удаляем BOM (Byte Order Mark) если есть
        if content.startswith('\ufeff'):
            content = content[1:]

        return content

    def write(self, file_path: Path, content: str, relative: bool = False):
        """
        Записывает Fluent-файл без BOM с корректными переносами строк

        Args:
            file_path: Путь к файлу
            content: Содержимое для записи
            relative: Использовать ли относительный путь от base_path
        """
        # Убеждаемся, что нет BOM
        if content.startswith('\ufeff'):
            content = content[1:]

        # Нормализуем переносы строк (LF вместо CRLF)
        content = content.replace('\r\n', '\n')

        # Убеждаемся, что файл заканчивается переносом строки
        if content and not content.endswith('\n'):
            content += '\n'

        super().write(file_path, content, relative)

    def parse_ast(self, file_path: Path, relative: bool = False) -> Resource:
        """
        Парсит Fluent-файл в AST

        Args:
            file_path: Путь к файлу
            relative: Использовать ли относительный путь от base_path

        Returns:
            Fluent AST Resource

        Raises:
            ValueError: Если в файле есть ошибки парсинга (Junk nodes)
        """
        content = self.read(file_path, relative)
        resource = parse(content)

        # Проверяем на наличие ошибок парсинга
        junk_nodes = [entry for entry in resource.body if isinstance(entry, Junk)]
        if junk_nodes:
            errors = []
            for junk in junk_nodes:
                errors.append(f"Строка {junk.span.start}: {junk.content}")
            raise ValueError(
                f"Ошибки парсинга в файле {file_path}:\n" + "\n".join(errors)
            )

        return resource

    def serialize_ast(self, resource: Resource) -> str:
        """
        Сериализует Fluent AST в строку с сохранением форматирования

        Args:
            resource: Fluent AST Resource

        Returns:
            Сериализованная строка
        """
        content = serialize(resource)

        # Убираем BOM если он появился
        if content.startswith('\ufeff'):
            content = content[1:]

        # Нормализуем переносы строк
        content = content.replace('\r\n', '\n')

        return content

    def write_ast(self, file_path: Path, resource: Resource, relative: bool = False):
        """
        Сериализует и записывает Fluent AST в файл

        Args:
            file_path: Путь к файлу
            resource: Fluent AST Resource
            relative: Использовать ли относительный путь от base_path
        """
        content = self.serialize_ast(resource)
        self.write(file_path, content, relative)

    def exists(self, file_path: Path, relative: bool = False) -> bool:
        """
        Проверяет существование файла

        Args:
            file_path: Путь к файлу
            relative: Использовать ли относительный путь от base_path

        Returns:
            True если файл существует
        """
        if relative:
            file_path = self.base_path / file_path

        return file_path.exists()
