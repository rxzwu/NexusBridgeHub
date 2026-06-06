# Публикация на PyPI

Краткий чеклист первого релиза и последующих обновлений.

## Что уже настроено в репозитории

| Файл | Назначение |
|------|------------|
| `pyproject.toml` | метаданные пакета, зависимости, entry points |
| `LICENSE` | MIT |
| `README.md` | long description на PyPI |
| `CHANGELOG.md` | история версий |
| `.github/workflows/ci.yml` | тесты на push/PR |
| `.github/workflows/publish.yml` | публикация на PyPI при GitHub Release |

## 1. Аккаунт PyPI

1. Зарегистрируйся на [pypi.org](https://pypi.org/account/register/)
2. Включи **2FA** (обязательно для загрузки)
3. Проверь, что имя **`nexusbridge`** свободно: [pypi.org/project/nexusbridge](https://pypi.org/project/nexusbridge/)

## 2. Trusted Publisher (рекомендуется)

Без пароля в GitHub Secrets — через OIDC:

1. PyPI → Account → **Publishing** → **Add a new pending publisher**
2. Заполни:
   - **PyPI Project Name:** `nexusbridge` (или оставь пустым для первого upload)
   - **Owner:** `rxzwu`
   - **Repository name:** `nexusbridge`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. Сохрани

## 3. Локальная проверка перед релизом

```bash
pip install -e ".[dev]"
pytest

python -m build
python -m twine check dist/*
```

Должно быть `PASSED` для wheel и sdist.

## 4. Релиз через GitHub (автоматически)

1. Обнови версию в **`src/nexusbridge/__init__.py`** (`__version__`) — `pyproject.toml` подхватит её автоматически
2. Допиши **`CHANGELOG.md`**
3. Закоммить, запушить в `main`
4. GitHub → **Releases** → **Draft a new release**
   - Tag: `v0.1.0` (с `v`)
   - Title: `0.1.0`
   - Описание: блок из CHANGELOG
5. **Publish release** → workflow `publish.yml` загрузит артефакты на PyPI

## 5. Ручная публикация (fallback)

```bash
python -m build
python -m twine upload dist/nexusbridge-0.1.0*
```

Потребуются API token PyPI (`pypi-...`) в переменной `TWINE_PASSWORD`, username `__token__`.

## 6. После публикации

```bash
pip install nexusbridge
nexusbridge-server --help
```

Badge **PyPI version** в README обновится в течение нескольких минут.

## Версионирование

- **PATCH** (0.1.1): багфиксы
- **MINOR** (0.2.0): новые фичи без ломающих изменений
- **MAJOR** (1.0.0): breaking changes

Один источник версии: `src/nexusbridge/__init__.py` → `__version__`.
