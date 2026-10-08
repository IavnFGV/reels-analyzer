# Ollama Devcontainer Reuse

## What is implemented here

This repository uses a repeatable devcontainer pattern for Ollama:

- Ollama binary is installed into the image in `.devcontainer/Dockerfile`.
- Python LLM client dependency is kept minimal: the project only needs `requests` from the `llm` extra in `pyproject.toml`.
- Host Ollama model cache is reused inside the container by bind-mounting `${localEnv:HOME}/.ollama` to `/home/vscode/.ollama`.
- Pip cache is also reused via a named Docker volume mounted to `/home/vscode/.cache/pip`.
- On every container start, `.devcontainer/start-ollama.sh` checks whether Ollama is already running, starts `ollama serve` if needed, waits for readiness on `http://127.0.0.1:11434/api/tags`, and pulls the configured model only if it is missing.
- Autostart and default model are controlled through `.devcontainer/ollama.env`, passed into the container with `--env-file`.
- Permissions for bind mounts and caches are normalized by `.devcontainer/fix-container-perms.sh`.
- GPU compatibility is checked before container startup in `.devcontainer/check-host-gpu.sh`. The GPU devcontainer profile fails early if Docker or the NVIDIA runtime is not ready on the host.
- CPU and GPU profiles are separated into `.devcontainer/devcontainer.cpu.json` and `.devcontainer/devcontainer.gpu.json`, with `scripts/switch-devcontainer-profile.sh` copying the selected profile into `.devcontainer/devcontainer.json`.

## How Ollama is called from Python

- The CLI exposes `--classify-text`, `--ollama-model`, and `--ollama-base-url`.
- Default endpoint is `http://localhost:11434/api/chat`.
- `src/reels_analyzer/reviewer.py` sends a non-streaming JSON chat request to Ollama with `requests.post(..., timeout=120)`.
- The project does not embed a Python Ollama SDK. It talks to Ollama over HTTP, which keeps the runtime lighter and more portable.

## How docker context is reduced

The devcontainer build context is still the repo root (`"context": ".."`), but `.dockerignore` removes heavy and irrelevant paths before Docker archives and transfers the context.

Current exclusions:

- `.git`
- `.pytest_cache`
- `.ruff_cache`
- `.vscode`
- `venv`
- `output`
- `projects`
- `docs`
- `__pycache__`
- Python bytecode files

This is the main protection against the "initializeCommand passed, then VS Code seems stuck" problem. The repo also contains a demo in `docs/devcontainer-context-mystery/` showing how a missing `.dockerignore` bloats `load build context`.

## How container startup is accelerated

The setup improves startup speed in several ways:

- Build image installs all heavy system tools up front: `curl`, `ffmpeg`, `zstd`, and Ollama.
- Build stage copies only `pyproject.toml` and `README.md` before dependency install, so dependency layers are reused unless project metadata changes.
- Docker BuildKit pip cache is used in the Dockerfile: `RUN --mount=type=cache,target=/root/.cache/pip ...`.
- Runtime pip cache is preserved between container rebuilds with a named volume.
- Host Ollama models are not copied into the image and are not redownloaded per project; they are reused through the bind mount.
- `postCreateCommand` runs `pip install -e . --no-deps`, so editable install is fast because main dependencies were already baked into the image.
- `start-ollama.sh` avoids duplicate startup and avoids pulling the model when it already exists.

## Reuse prompt

Use this prompt in another project when you want the same approach implemented instead of a fresh ad hoc design:

```text
Проанализируй текущий проект и внедри в нём devcontainer-паттерн для Ollama по образцу из моего проекта reels-analyzer. Ничего не придумывай заново без причины: повтори уже проверенные решения и явно отмечай, если что-то приходится адаптировать под структуру нового репозитория.

Цели:
1. Установить Ollama внутрь devcontainer image.
2. Сделать проброс кэша моделей с хоста в контейнер через bind mount `${localEnv:HOME}/.ollama -> /home/vscode/.ollama`, чтобы модели не скачивались заново в каждом проекте.
3. Сделать отдельный mount для pip cache, чтобы ускорить rebuild/start.
4. Добавить `postStartCommand`, который:
   - чинит права на bind-mounted каталоги и cache;
   - проверяет, запущен ли Ollama;
   - если нет, запускает `ollama serve`;
   - ждёт readiness по HTTP;
   - при необходимости подтягивает модель из переменной окружения;
   - не тянет модель повторно, если она уже есть.
5. Настроить `.devcontainer/ollama.env` с минимумом таких переменных:
   - `OLLAMA_AUTOSTART=1`
   - `OLLAMA_PULL_MODEL=<подходящая модель по умолчанию>`
6. Если в проекте нужен GPU-профиль:
   - сделать отдельные CPU/GPU devcontainer profile json-файлы;
   - для GPU добавить `--gpus all`;
   - добавить preflight-скрипт, который до старта контейнера валидирует `docker`, `nvidia-smi` и наличие `nvidia` runtime в Docker;
   - сделать переключатель профиля через shell script.
7. Для Python-интеграции с Ollama не тащи тяжёлый SDK без необходимости:
   - предпочитай HTTP-вызов к `http://localhost:11434/api/chat`;
   - добавь только минимальную Python-зависимость, например `requests`, как optional extra `llm`.
8. Сократи docker build context:
   - проверь `.dockerignore`;
   - исключи большие или нерелевантные директории вроде `.git`, `docs`, `projects`, `output`, кэши, виртуальные окружения и bytecode;
   - объясни, что это нужно для ускорения `load build context`.
9. Ускорь build/start контейнера:
   - зависимости ставь в image layer заранее;
   - используй BuildKit cache для pip;
   - editable install проекта после создания контейнера делай через `pip install -e . --no-deps`, если зависимости уже baked into image.

Требования к реализации:
- Не хардкодь абсолютные пути workspace.
- Пути в shell-скриптах должны вычисляться относительно расположения скрипта или текущего repo root.
- Не ломай существующую структуру проекта без необходимости.
- Если в новом проекте уже есть devcontainer, аккуратно адаптируй его, а не переписывай вслепую.
- Перед изменениями сначала покажи, какие файлы отвечают за devcontainer/build/startup/dependencies.
- После изменений перечисли:
  - какие файлы созданы/изменены;
  - как именно работает старт Ollama;
  - как устроен reuse host models;
  - как уменьшён docker context;
  - чем ускорены build и startup;
  - как проверить CPU и GPU сценарии.

Если увидишь, что в новом репозитории есть ограничения, отличающиеся от reels-analyzer, сначала кратко объясни адаптацию, потом внедряй совместимую версию того же паттерна.
```
