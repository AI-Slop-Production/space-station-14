# SS14RU Fluent Localization Utility

Комплексная утилита для автоматизации работы с Fluent-локализацией в проекте Space Station 14.

## Возможности

- Автоматическая генерация Fluent-файлов из YAML-прототипов
- Синхронизация локалей между en-US и ru-RU
- Поддержка сабмодуля RobustToolbox
- Очистка дублирующихся ключей (включая кросс-файловый поиск)
- Удаление устаревших ключей (orphan cleanup)
- Удаление пустых файлов и директорий
- Нормализация тире в переводах
- Поддержка parent references для YAML-сущностей
- Обработка YAML-файлов с табуляцией
- Интеграция с Lokalise (экспериментально)
- Форматирование Fluent-файлов в единый стиль

## Структура проекта

```
Tools/ss14ru/
├── requirements.txt      # Зависимости Python
├── run.py               # Главный скрипт запуска
├── README.md            # Документация
├── fix_duplicated_keys.py  # Скрипт для исправления дублированных ключей
└── src/                 # Исходный код
    ├── config.py        # Конфигурация и пути
    ├── file_handlers.py # Обработчики файлов
    ├── yaml_handler.py  # Работа с YAML
    ├── models.py        # Модели данных
    ├── fluent_serializer.py  # Сериализация Fluent
    ├── fluent_formatter.py   # Форматирование
    ├── yaml_processor.py     # Обработка прототипов
    ├── locale_sync.py        # Синхронизация локалей
    ├── cleanup_duplicates.py # Очистка дубликатов
    ├── cleanup_orphans.py    # Очистка устаревших ключей
    ├── cleanup_empty.py      # Очистка пустых файлов
    ├── normalize_dashes.py   # Нормализация тире
    ├── lokalise_client.py    # Клиент Lokalise
    ├── ast_manager.py        # Работа с AST
    └── merger.py             # Слияние переводов
```

## Установка и запуск

### Быстрый старт

```bash
# Переходим в директорию утилиты
cd Tools/ss14ru

# Устанавливаем зависимости и запускаем все этапы
python3 run.py --install-deps

# Или устанавливаем зависимости отдельно
pip install -r requirements.txt

# Запуск всех этапов обработки
python3 run.py
```

### Доступные команды

```bash
# Запустить все этапы
python3 run.py

# Запустить конкретный этап
python3 run.py --step generate        # Генерация из YAML
python3 run.py --step sync            # Синхронизация локалей
python3 run.py --step cleanup-dupes   # Очистка дубликатов
python3 run.py --step cleanup-orphans # Очистка устаревших ключей
python3 run.py --step cleanup-empty   # Очистка пустых файлов
python3 run.py --step normalize       # Нормализация тире

# Режим предпросмотра (без изменений)
python3 run.py --dry-run

# Подробный вывод
python3 run.py -v

# Дополнительные опции
python3 run.py --no-create         # Не создавать русские файлы при синхронизации
python3 run.py --no-warnings       # Не выводить предупреждения об orphan-ключах
python3 run.py --skip-normalize    # Пропустить нормализацию тире
```

### Исправление дублированных ключей

Если у вас есть файлы с ошибкой дублирования (например, `ent-Key = ent-Key = value`):

```bash
# Исправить все файлы в ru-RU
python3 fix_duplicated_keys.py

# Предпросмотр без изменений
python3 fix_duplicated_keys.py --dry-run

# Подробный вывод
python3 fix_duplicated_keys.py -v
```

## Этапы обработки

### 1. Генерация из YAML-прототипов

Сканирует все YAML-файлы в `Resources/Prototypes`, извлекает локализуемые поля (`name`, `description`, `suffix`, `parent`) и генерирует соответствующие Fluent-файлы.

**Правила группировки YAML файлов:**
- Файлы группируются по родительской папке
- Например: `Resources/Prototypes/Entities/Clothing/Back/backpacks.yml` → `Resources/Locale/ru-RU/ss14-ru/Entities/Clothing/back.ftl`
- Все YAML из одной папки попадают в один `.ftl` файл

**Особенности:**
- Создаются записи для **всех** entity, даже если у них нет локализуемых полей
- Поддержка parent references: `ent-WallBrick = { ent-BaseWall }`
- Корректная обработка цепочек наследования (parent chains)
- Автоматическое добавление префикса `ent-` к parent ID

**Результат:**
- Создается папка `Resources/Locale/ru-RU/ss14-ru/` со всеми локалями
- Автоматически создаются русские копии на основе английских

### 2. Синхронизация локалей

Синхронизирует файлы между `en-US` и `ru-RU` из двух источников:

**1. Основные локали:**
- `Resources/Locale/en-US` → `Resources/Locale/ru-RU`

**2. RobustToolbox (сабмодуль):**
- `RobustToolbox/Resources/Locale/en-US` → `Resources/Locale/ru-RU/robust-toolbox`

**Функционал:**
- Создает отсутствующие русские файлы (зеркальная структура)
- Добавляет недостающие ключи и атрибуты из английской версии
- Предупреждает об orphan-ключах (ключи только в ru-RU)
- Форматирует обновленные файлы
- Поддержка как Messages, так и Terms (с префиксом `-`)

**Правила для готовых FTL файлов:**
- Файлы из `Resources/Locale/en-US` копируются в `Resources/Locale/ru-RU` с сохранением точной структуры каталогов
- Файлы из сабмодуля RobustToolbox помещаются в отдельную папку `ru-RU/robust-toolbox/`

### 3. Очистка дубликатов

Сканирует Fluent-файлы и удаляет дублирующиеся блоки сообщений:

**Возможности:**
- **Кросс-файловый поиск**: находит дубликаты между разными файлами
- Определяет корректное местоположение на основе en-US
- По умолчанию сохраняет вхождение из правильного файла
- Удаляет связанные комментарии
- Ведет лог изменений

**Обработка модификаций:**
- Файлы из `_DV`, `nyanotrasen` и других модов учитываются
- Приоритет отдается основному файлу (не модификации)

### 4. Очистка устаревших ключей (orphan cleanup)

Удаляет ключи, которых больше нет в исходных файлах:

**Для файлов из YAML (ss14-ru/):**
- Сканирует все YAML-прототипы в `Resources/Prototypes`
- Удаляет ключи сущностей, которые больше не существуют
- Поддержка консолидированных файлов (несколько YAML → один FTL)
- Частичное удаление (один entity удален из YAML → только его ключ удален из FTL)

**Для обычных локалей (не ss14-ru):**
- Сверяет ru-RU с en-US файлами
- Удаляет ключи, отсутствующие в en-US
- Удаляет orphan файлы (ru-RU без соответствующего en-US)

**Особенности:**
- Поддержка многострочных ключей (книги, описания)
- Поддержка Fluent selectors (`{$count -> [1]one *[other]many}`)
- Обработка YAML с табуляцией (временная замена на пробелы)
- Работает с RobustToolbox файлами в `ru-RU/robust-toolbox/`

**Статистика:**
- Количество обработанных файлов
- Количество удаленных ключей
- Количество удаленных orphan файлов
- Количество YAML файлов с ошибками парсинга

### 5. Очистка пустых файлов

Находит и удаляет:
- Пустые `.ftl` файлы (без сообщений)
- Пустые директории после удаления файлов
- Работает рекурсивно снизу вверх

**Порядок важен:** этап идет после очистки orphan-ключей, чтобы удалить файлы, которые могли опустеть после удаления ключей.

### 6. Нормализация тире

Заменяет дефисы между пробелами на длинное тире (—):
- Пропускает комментарии (строки с `#`)
- Пропускает маркеры списков
- Сохраняет форматирование

## Структура кода

### Основные компоненты

#### ProjectConfig (config.py)
- Автоопределение корня проекта по маркерному файлу `SpaceStation14.sln`
- Вычисление абсолютных путей к ресурсам
- Поддержка путей RobustToolbox
- Интеллектуальное зеркалирование путей (en-US ↔ ru-RU)
- Сбор списков Fluent и YAML файлов

#### FileHandlers (file_handlers.py)
- `TextFileHandler` - базовый обработчик текстовых файлов
- `FluentFileHandler` - специализированный для Fluent с поддержкой BOM, AST

#### YAMLHandler (yaml_handler.py)
- Безопасная загрузка YAML
- Извлечение локализуемых полей
- Поддержка parent field
- Обработка всех entity (не только с полями)

#### Models (models.py)
- `LocalizableEntity` - модель сущности из YAML
- `FluentMessage` - модель Fluent-сообщения
- `TranslationKey` - модель ключа перевода из внешней системы
- Поддержка parent references

#### FluentSerializer (fluent_serializer.py)
- Преобразование YAML-сущностей в Fluent-сообщения
- Автоматическое добавление комментариев
- Поддержка ссылок на родительские значения с префиксом `ent-`
- Создание пустых ссылок `{ "" }` для entity без полей
- Группировка атрибутов

#### FluentFormatter (fluent_formatter.py)
- Парсинг и сериализация Fluent-файлов
- Нормализация (удаление BOM, переносы строк)
- Пакетное форматирование

#### OrphanCleaner (cleanup_orphans.py)
- Сбор entity ID из YAML-прототипов
- Извлечение ключей из en-US файлов
- Умное удаление orphan-ключей и атрибутов
- Поддержка многострочных записей
- Обработка YAML с табуляцией
- Удаление orphan файлов
- Поддержка RobustToolbox путей

#### DuplicateCleaner (cleanup_duplicates.py)
- Кросс-файловый поиск дубликатов
- Определение правильного местоположения на основе en-US
- Умное удаление с сохранением комментариев

## Примеры использования

### Программное использование

```python
from src.config import get_config
from src.yaml_processor import YAMLProcessor

# Получаем конфигурацию
config = get_config()

# Обрабатываем YAML-прототипы
processor = YAMLProcessor(config)
stats = processor.generate_all_locales()

print(f"Создано {stats['created']} файлов")
print(f"Обновлено {stats['updated']} файлов")
```

### Работа с отдельными модулями

```python
from src.locale_sync import LocaleSync
from src.cleanup_duplicates import DuplicateCleaner
from src.cleanup_orphans import OrphanCleaner

# Синхронизация (включая RobustToolbox)
syncer = LocaleSync(config)
syncer.sync_all()

# Очистка дубликатов (кросс-файловая)
cleaner = DuplicateCleaner(config)
cleaner.clean_all(locale_dir=config.ru_ru_locale)

# Очистка orphan-ключей
orphan_cleaner = OrphanCleaner(config)
orphan_cleaner.clean_all()
```

### Работа с RobustToolbox

```python
# Проверка путей RobustToolbox
print(f"RobustToolbox en-US: {config.robust_toolbox_en_us}")
print(f"RobustToolbox ru-RU: {config.ru_ru_robust_toolbox}")

# Зеркалирование путей автоматическое
en_path = config.robust_toolbox_en_us / "some/file.ftl"
ru_path = config.get_mirrored_locale_path(en_path)
# Результат: Resources/Locale/ru-RU/robust-toolbox/some/file.ftl
```

## Требования

- Python 3.8+
- fluent.syntax >= 0.19.0
- PyYAML >= 6.0
- requests >= 2.31.0 (для интеграции с Lokalise)

## Результаты работы

После успешного выполнения утилиты:
- Создается структура `Resources/Locale/ru-RU/` с полной локализацией
- Синхронизируются файлы из RobustToolbox в `ru-RU/robust-toolbox/`
- Все файлы форматируются в единый стиль
- Отсутствуют дубликаты и устаревшие ключи
- Отсутствуют пустые файлы
- Ключи синхронизированы с английской версией
- Все parent references корректны

## Логирование

Утилита ведет подробное логирование:
- Уровень INFO: основные события, статистика
- Уровень WARNING: orphan-ключи, файлы с табуляцией, потенциальные проблемы
- Уровень ERROR: ошибки обработки, парсинга

Включите подробный режим с флагом `-v` для отладки.

## Разработка

### Добавление нового этапа

1. Создайте модуль в `src/`
2. Реализуйте основную логику с методом `clean_all()` или аналогичным
3. Добавьте функцию-обертку в `run.py`
4. Добавьте этап в цепочку выполнения
5. Обновите документацию

### Тестирование

Используйте `--dry-run` для тестирования без изменений:

```bash
python3 run.py --dry-run -v
```

Тестирование отдельных этапов:

```bash
# Только orphan cleanup
python3 run.py --step cleanup-orphans --dry-run -v

# Только дубликаты
python3 run.py --step cleanup-dupes --dry-run -v
```

## Известные особенности

### YAML с табуляцией
YAML спецификация не поддерживает табуляцию. Утилита автоматически обрабатывает такие файлы:
- Временно заменяет табы на пробелы
- Извлекает entity ID
- Логирует предупреждение

### Консолидированные файлы
Несколько YAML из одной папки объединяются в один FTL:
- `Chapel/urn.yml` + `Chapel/altar.yml` → `Chapel.ftl`
- При удалении одного YAML удаляются только его ключи, не весь файл

### Parent chains
Цепочки наследования обрабатываются корректно:
- `WallBrick → BaseWall → BaseStructureWall`
- Создаются промежуточные entity даже без полей
- Добавляется префикс `ent-` к parent ID

## Поддержка

При возникновении проблем:
1. Проверьте логи с флагом `-v`
2. Убедитесь, что все зависимости установлены
3. Проверьте структуру проекта (наличие маркерного файла)
4. Используйте `--dry-run` для диагностики

## Лицензия

Утилита является частью проекта Space Station 14.

## Авторы

Разработано для SS14RU сообщества.
