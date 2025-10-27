"""
Форматер для Fluent-файлов
"""

from pathlib import Path
from fluent.syntax import parse, serialize
from fluent.syntax.ast import Resource
from .file_handlers import FluentFileHandler


class FluentFormatter:
    """Форматер для парсинга и сериализации Fluent-файлов в единый стиль"""

    def __init__(self):
        """Инициализация форматера"""
        self.handler = FluentFileHandler()

    def format_file(self, file_path: Path) -> str:
        """
        Форматирует Fluent-файл, парсит и обратно сериализует

        Args:
            file_path: Путь к файлу для форматирования

        Returns:
            Отформатированное содержимое
        """
        # Читаем и парсим файл
        content = self.handler.read(file_path)
        resource = parse(content)

        # Сериализуем обратно
        formatted = serialize(resource)

        # Нормализуем: убираем BOM, нормализуем переносы строк
        formatted = self._normalize(formatted)

        return formatted

    def format_string(self, content: str) -> str:
        """
        Форматирует строку Fluent-контента (режим постобработки)

        Args:
            content: Строка с Fluent-контентом

        Returns:
            Отформатированная строка
        """
        # Парсим строку
        resource = parse(content)

        # Сериализуем обратно
        formatted = serialize(resource)

        # Нормализуем
        formatted = self._normalize(formatted)

        return formatted

    def format_ast(self, resource: Resource) -> str:
        """
        Форматирует Fluent AST Resource

        Args:
            resource: Fluent AST Resource

        Returns:
            Отформатированная строка
        """
        formatted = serialize(resource)
        formatted = self._normalize(formatted)
        return formatted

    def format_and_save(self, file_path: Path, output_path: Path = None):
        """
        Форматирует файл и сохраняет результат

        Args:
            file_path: Путь к исходному файлу
            output_path: Путь для сохранения (если None, перезаписывает исходный)
        """
        formatted = self.format_file(file_path)

        if output_path is None:
            output_path = file_path

        self.handler.write(output_path, formatted)

    def _normalize(self, content: str) -> str:
        """
        Нормализует содержимое Fluent-файла

        Args:
            content: Содержимое для нормализации

        Returns:
            Нормализованное содержимое
        """
        # Убираем BOM если есть
        if content.startswith('\ufeff'):
            content = content[1:]

        # Нормализуем переносы строк (LF вместо CRLF)
        content = content.replace('\r\n', '\n')

        # Убираем множественные пустые строки (больше 2 подряд)
        while '\n\n\n\n' in content:
            content = content.replace('\n\n\n\n', '\n\n\n')

        # Убеждаемся, что файл заканчивается одним переносом строки
        content = content.rstrip('\n') + '\n'

        return content

    def validate_file(self, file_path: Path) -> bool:
        """
        Проверяет, можно ли успешно распарсить файл

        Args:
            file_path: Путь к файлу для проверки

        Returns:
            True если файл валиден, False иначе
        """
        try:
            content = self.handler.read(file_path)
            resource = parse(content)
            # Проверяем на наличие Junk nodes (ошибки парсинга)
            from fluent.syntax.ast import Junk
            junk_nodes = [entry for entry in resource.body if isinstance(entry, Junk)]
            return len(junk_nodes) == 0
        except Exception:
            return False

    def batch_format(self, file_paths: list[Path], in_place: bool = True):
        """
        Форматирует множество файлов

        Args:
            file_paths: Список путей к файлам
            in_place: Форматировать файлы на месте (True) или вернуть результаты (False)

        Returns:
            Если in_place=False, возвращает словарь {file_path: formatted_content}
        """
        if in_place:
            for file_path in file_paths:
                try:
                    self.format_and_save(file_path)
                except Exception as e:
                    print(f"Ошибка форматирования {file_path}: {e}")
            return None
        else:
            results = {}
            for file_path in file_paths:
                try:
                    results[file_path] = self.format_file(file_path)
                except Exception as e:
                    print(f"Ошибка форматирования {file_path}: {e}")
            return results
