# Cache Eraser

[![CI](https://github.com/GLADOSKABOSS/cache_eraser/actions/workflows/ci.yml/badge.svg)](https://github.com/GLADOSKABOSS/cache_eraser/actions/workflows/ci.yml)
[![CD](https://github.com/GLADOSKABOSS/cache_eraser/actions/workflows/cd.yml/badge.svg)](https://github.com/GLADOSKABOSS/cache_eraser/actions/workflows/cd.yml)
[![Pylint](https://img.shields.io/badge/pylint-10.00-brightgreen)](https://github.com/GLADOSKABOSS/cache_eraser/blob/main/.pylintrc)

GUI-утилита для рекурсивного поиска и удаления кеш-файлов и артефактов сборки в указанной директории.

## Возможности

- **19 типов кеша**: `__pycache__`, `.mypy_cache`, `build/`, `.next/`, `.ruff_cache`, `.pytest_cache` и другие.
- **Выборочное сканирование**: включите/отключите нужные типы кеша через чекбоксы.
- **Dry-run режим**: просмотрите что будет удалено без фактического удаления.
- **Сортировка по размеру**: найденные элементы отсортированы от крупных к мелким.
- **Безопасность**: `.git`, `node_modules`, `venv`, `dist/`, `output/` и другие важные директории исключены из обхода.
- **Single exe**: собран через PyInstaller, не требует Python для запуска.

## Использование

1. Скачайте последний релиз со страницы [Releases](https://github.com/GLADOSKABOSS/cache_eraser/releases).
2. Запустите `CacheEraser.exe`.
3. Выберите корневую директорию для сканирования (кнопка **Browse**).
4. Отметьте нужные типы кеша (все включены по умолчанию).
5. Нажмите **Scan** — программа найдёт все совпадения и покажет их в таблице с размерами.
6. Включите **Dry run**, если хотите только просмотреть результаты без удаления.
7. Нажмите **Delete All** для безвозвратного удаления (потребуется подтверждение).

## Сборка из исходников

```powershell
pip install pyinstaller
python -m PyInstaller CacheEraser.spec
```

Или через bat-файл:

```powershell
build_exe.bat
```

Готовый exe появится в корне проекта.

## CI / CD

При пуше в `main` выполняются:

| Этап | Инструменты | Статус |
|---|---|---|
| **lint** | ruff, mypy, pylint | pylint **10.00/10** |
| **test** | pytest, pytest-cov | покрытие ≥ 70% |
| **build** | PyInstaller | Windows exe |
| **release** | GitHub Releases | публикация релиза |

Сборка и релиз запускаются только при изменении исходного кода (`main.py`, `scanner.py`, `cache_patterns.py`, `CacheEraser.spec`, `icon.png`).

## Структура проекта

| Файл | Назначение |
|---|---|
| `main.py` | GUI на tkinter (ttk) |
| `scanner.py` | Рекурсивный обход, подсчёт размера, удаление |
| `cache_patterns.py` | Определения типов кеша и исключённых директорий |
| `CacheEraser.spec` | Спецификация PyInstaller |
| `build_exe.bat` | Скрипт сборки |
| `icon.png` | Иконка приложения |
| `CacheEraser.exe` | Готовый исполняемый файл |
| `.pylintrc` | Конфигурация pylint (10.00/10) |
| `tests/` | Модульные тесты |
| `.github/workflows/` | CI/CD пайплайны |

## Исключённые директории

Следующие директории полностью пропускаются при сканировании (включая всё их содержимое):

- `.git` — репозиторий
- `node_modules` — зависимости npm
- `venv`, `.venv`, `env`, `.env` — виртуальные окружения Python
- `dist`, `output` — сборочные артефакты
