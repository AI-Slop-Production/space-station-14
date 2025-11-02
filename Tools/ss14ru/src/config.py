"""
Конфигурация проекта и управление путями
"""

import os
from pathlib import Path
from typing import List, Optional


class ProjectConfig:
    """Конфигурация проекта с автоопределением корневой папки"""

    # Маркерный файл для определения корня проекта
    MARKER_FILE = "SpaceStation14.sln"

    def __init__(self, start_path: Optional[Path] = None):
        """
        Инициализация конфигурации проекта

        Args:
            start_path: Начальная директория для поиска корня проекта
        """
        self.start_path = start_path or Path(__file__).resolve().parent.parent.parent.parent
        self.project_root = self._find_project_root()

        # Основные пути
        self.resources_dir = self.project_root / "Resources"
        self.prototypes_dir = self.resources_dir / "Prototypes"
        self.locale_dir = self.resources_dir / "Locale"

        # RobustToolbox (сабмодуль)
        self.robust_toolbox_dir = self.project_root / "RobustToolbox"
        self.robust_toolbox_resources = self.robust_toolbox_dir / "Resources"
        self.robust_toolbox_locale = self.robust_toolbox_resources / "Locale"
        self.robust_toolbox_en_us = self.robust_toolbox_locale / "en-US"

        # Рабочие локали
        self.en_us_locale = self.locale_dir / "en-US"
        self.ru_ru_locale = self.locale_dir / "ru-RU"
        self.ru_ru_ss14_locale = self.ru_ru_locale / "ss14-ru"
        self.ru_ru_robust_toolbox = self.ru_ru_locale / "robust-toolbox"

    def _find_project_root(self) -> Path:
        """
        Определяет корневую папку проекта по маркерному файлу

        Returns:
            Path к корневой папке проекта

        Raises:
            FileNotFoundError: Если маркерный файл не найден
        """
        current = self.start_path

        # Идем вверх по дереву директорий
        while current != current.parent:
            marker_path = current / self.MARKER_FILE
            if marker_path.exists():
                return current
            current = current.parent

        # Проверяем корень системы
        if (current / self.MARKER_FILE).exists():
            return current

        raise FileNotFoundError(
            f"Не удалось найти корень проекта. "
            f"Маркерный файл '{self.MARKER_FILE}' не найден."
        )

    def get_prototype_files(self) -> List[Path]:
        """
        Собирает список всех YAML-файлов прототипов

        Returns:
            Список путей к YAML-файлам
        """
        yaml_files = []

        if not self.prototypes_dir.exists():
            return yaml_files

        # Рекурсивно собираем все .yml файлы
        for yaml_file in self.prototypes_dir.rglob("*.yml"):
            yaml_files.append(yaml_file)

        return sorted(yaml_files)

    def get_fluent_files(self, locale_dir: Path) -> List[Path]:
        """
        Собирает список всех Fluent-файлов в указанной локали

        Args:
            locale_dir: Директория локали для сканирования

        Returns:
            Список путей к .ftl файлам
        """
        ftl_files = []

        if not locale_dir.exists():
            return ftl_files

        # Рекурсивно собираем все .ftl файлы
        for ftl_file in locale_dir.rglob("*.ftl"):
            ftl_files.append(ftl_file)

        return sorted(ftl_files)

    def get_locale_path_from_prototype(self, prototype_path: Path) -> Path:
        """
        Вычисляет путь к файлу локализации для YAML-прототипа.

        Правило: для YAML файлов группируем по родительской папке.
        Например:
        - Resources/Prototypes/Entities/Clothing/Back/backpacks.yml
          -> Resources/Locale/ru-RU/ss14-ru/Entities/Clothing/back.ftl
        - Resources/Prototypes/Entities/Objects/Devices/Circuitboards/Machine/foo.yml
          -> Resources/Locale/ru-RU/ss14-ru/Entities/Objects/Devices/Circuitboards/machine.ftl

        Args:
            prototype_path: Путь к YAML-файлу прототипа

        Returns:
            Путь к соответствующему .ftl файлу
        """
        # Получаем относительный путь от Prototypes/
        relative = prototype_path.relative_to(self.prototypes_dir)

        # Получаем части пути
        parts = relative.parts[:-1]  # Убираем имя файла

        if not parts:
            # Файл находится прямо в Prototypes/
            ftl_name = prototype_path.stem + ".ftl"
            return self.ru_ru_ss14_locale / ftl_name

        # Берем имя последней папки в нижнем регистре как имя файла
        ftl_name = parts[-1].lower() + ".ftl"

        # Строим путь к локали
        locale_subpath = Path(*parts[:-1]) if len(parts) > 1 else Path(".")

        if locale_subpath == Path("."):
            return self.ru_ru_ss14_locale / ftl_name

        return self.ru_ru_ss14_locale / locale_subpath / ftl_name

    def get_mirrored_locale_path(self, en_us_path: Path, create_dirs: bool = False) -> Path:
        """
        Получает зеркальный путь для файла из en-US в ru-RU.
        Сохраняет точную структуру каталогов.

        Обрабатывает два случая:
        1. Обычные локали: Resources/Locale/en-US/foo.ftl -> Resources/Locale/ru-RU/foo.ftl
        2. RobustToolbox: RobustToolbox/Resources/Locale/en-US/foo.ftl -> Resources/Locale/ru-RU/robust-toolbox/foo.ftl

        Args:
            en_us_path: Путь к файлу в en-US
            create_dirs: Создавать ли промежуточные директории

        Returns:
            Соответствующий путь в ru-RU
        """
        # Проверяем, из RobustToolbox ли этот файл
        try:
            relative = en_us_path.relative_to(self.robust_toolbox_en_us)
            # Это файл из RobustToolbox - помещаем в robust-toolbox/
            ru_path = self.ru_ru_robust_toolbox / relative
        except ValueError:
            # Это обычный файл - получаем относительный путь от en-US
            relative = en_us_path.relative_to(self.en_us_locale)
            ru_path = self.ru_ru_locale / relative

        if create_dirs:
            ru_path.parent.mkdir(parents=True, exist_ok=True)

        return ru_path

    def ensure_directories(self):
        """Создает необходимые директории для работы"""
        self.ru_ru_locale.mkdir(parents=True, exist_ok=True)
        self.ru_ru_ss14_locale.mkdir(parents=True, exist_ok=True)
        self.ru_ru_robust_toolbox.mkdir(parents=True, exist_ok=True)


# Глобальный экземпляр конфигурации
_config: Optional[ProjectConfig] = None


def get_config() -> ProjectConfig:
    """
    Получает глобальный экземпляр конфигурации проекта

    Returns:
        Экземпляр ProjectConfig
    """
    global _config
    if _config is None:
        _config = ProjectConfig()
    return _config


def reset_config():
    """Сбрасывает глобальный экземпляр конфигурации"""
    global _config
    _config = None
