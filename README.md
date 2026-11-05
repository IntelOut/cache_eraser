# Cache Eraser

[![CI](https://github.com/IntelOut/cache_eraser/actions/workflows/ci.yml/badge.svg)](https://github.com/IntelOut/cache_eraser/actions/workflows/ci.yml)
[![CD](https://github.com/IntelOut/cache_eraser/actions/workflows/cd.yml/badge.svg)](https://github.com/IntelOut/cache_eraser/actions/workflows/cd.yml)
[![Pylint](https://img.shields.io/badge/pylint-10.00-brightgreen)](https://github.com/IntelOut/cache_eraser/blob/main/.pylintrc)

GUI-утилита для рекурсивного поиска и удаления кеш-файлов и артефактов сборки в указанной директории.

## Возможности

- **37 типов кеша** с группировкой по экосистемам: Python, JavaScript, Build, Mobile, Infrastructure.
- **Уровни риска**: безопасные типы включены по умолчанию, потенциально опасные (`build/`, `target/`, `.cache`, `obj/`, `Pods/`) помечены `⚠` и выключены.
- **Выборочное сканирование**: чекбоксы типов кеша и кнопки «Safe only» / «Unselect all».
- **Dry-run режим**: просмотр результатов без удаления.
- **Удаление выбранного или всего**: «Delete Selected» и «Delete All» с подтверждением.
- **Корзина по выбору**: «Move to Recycle Bin» вместо безвозвратного удаления (по умолчанию выключено).
- **Прогресс и отмена**: счётчик просканированных каталогов и кнопка Cancel (Esc).
- **Безопасность**: `.git`, `node_modules`, виртуальные окружения и сборочные каталоги исключены; симлинки/junction-точки не обходятся и не удаляются; удаление за пределами выбранного корня запрещено.
- **Windows long paths**: поддержка путей длиннее 260 символов.
- **Учёт ошибок доступа**: пропущенные элементы и недоступные каталоги учитываются в статусе, кнопка **Details** показывает подробности.
- **UX**: сортировка по клику на заголовок, двойной клик — открыть расположение, контекстное меню, копирование пути, горячие клавиши `F5` / `Ctrl+A` / `Del` / `Esc`, подсказки с описанием типов.
- **Без следов на диске**: настройки и логи не сохраняются, приложение не создаёт конфигов и лог-файлов.
- **Single exe**: собирается через PyInstaller, Python для запуска не требуется.

## Использование

1. Скачайте последний релиз со страницы [Releases](https://github.com/IntelOut/cache_eraser/releases).
2. Запустите `CacheEraser.exe`.
3. Выберите корневую директорию (кнопка **Browse**).
4. Отметьте нужные типы кеша.
5. Нажмите **Scan (F5)** — результаты появятся в таблице с размерами.
6. Включите **Dry run**, если хотите только просмотреть результаты.
7. При необходимости включите **Move to Recycle Bin**, иначе удаление будет безвозвратным. Для путей длиннее 260 символов корзина Windows недоступна — используйте безвозвратное удаление.
8. Выберите строки и нажмите **Delete Selected (Del)** или **Delete All**.

## Сборка из исходников

Требования: Python 3.12+, PyInstaller, Pillow, [UPX](https://upx.github.io/) (опционально, PyInstaller найдёт его через `PATH`).

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller CacheEraser.spec
```

Или через bat-файл:

```powershell
build_exe.bat
```

Готовый exe появится в `dist/CacheEraser.exe`.

## Тесты и проверки

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest --cov=cache_eraser --cov-fail-under=85
ruff check .
ruff format --check .
mypy
pylint cache_eraser main.py cache_patterns.py scanner.py tests/
```

Минимальное покрытие — **85%** (также задано в `pyproject.toml`). Опционально: `pre-commit install`.

## CI / CD

| Workflow | Условие | Инструменты |
|---|---|---|
| `ci.yml` | push / pull request | ruff, format, mypy, pylint, pytest с покрытием ≥ 85% на Ubuntu и Windows |
| `cd.yml` | вручную (workflow_dispatch) | тесты → PyInstaller + UPX → GitHub Release с exe |

CD запускается с обязательным входным параметром версии (например, `v0.3.0`) и не выпускает релиз при падении тестов. К релизу прикладывается `CacheEraser.exe.sha256` для проверки целостности.

## Структура проекта

| Путь | Назначение |
|---|---|
| `cache_eraser/ui.py` | GUI на tkinter (ttk) |
| `cache_eraser/scanner.py` | Рекурсивный обход, подсчёт размера, прогресс, отмена |
| `cache_eraser/deleter.py` | Удаление, корзина, проверки безопасности |
| `cache_eraser/patterns.py` | Типы кеша, категории, уровни риска, исключения |
| `cache_eraser/formatter.py` | Форматирование размеров (KiB/MiB/GiB) |
| `cache_eraser/paths.py` | Long paths, containment, обнаружение ссылок |
| `cache_eraser/ui_logic.py` | Чистые проверки состояния UI |
| `main.py` | Точка входа |
| `cache_patterns.py`, `scanner.py` | Совместимые реэкспорты старых модулей |
| `CacheEraser.spec` | Спецификация PyInstaller |
| `version_info.txt` | Метаданные версии exe |
| `icon.png`, `icon.ico` | Иконки приложения |
| `pyproject.toml` | Конфигурация ruff, mypy, pytest, coverage |
| `requirements.txt`, `requirements-dev.txt`, `requirements-build.txt` | Зависимости |
| `.pre-commit-config.yaml` | Pre-commit хуки |
| `tests/` | Модульные тесты |
| `.github/workflows/` | CI/CD пайплайны |
| `.github/dependabot.yml` | Автообновление зависимостей |

## Ограничение ответственности

Утилита удаляет файлы и каталоги. При выключенном **Move to Recycle Bin** удаление необратимо. Вы используете программу **на свой страх и риск**: авторы не несут ответственности за потерю данных, повреждение проектов или любой другой ущерб, вызванный использованием или невозможностью использования программы.

Перед массовым удалением проверяйте результаты в **Dry run** и делайте резервные копии. Программа предоставляется «как есть», без каких-либо гарантий, явных или подразумеваемых.

## Исключённые директории

Следующие директории полностью пропускаются при сканировании (включая всё их содержимое):

- `.git`, `.hg`, `.svn` — репозитории;
- `node_modules` — зависимости npm;
- `venv`, `.venv`, `env`, `.env` — виртуальные окружения Python;
- `dist`, `output` — сборочные артефакты.
