# Continue From Container

Use this prompt in a new Codex chat after reopening the project in the devcontainer:

```text
Работаем в проекте reels-analyzer.

Контекст:
- проект открыт уже внутри devcontainer;
- базовый CLI: `reels-analyzer run --channel <name> --links-file <path>`;
- optional extras ставятся отдельно через `./scripts/install-extras.sh video|transcription|llm|all`;
- текущая цель: довести pipeline от `links.txt` до удобного анализа данных без хаоса в структуре проекта;
- модели в проекте должны оставаться в отдельных файлах, не собранными в один большой `models.py`;
- если меняешь архитектуру, делай минимально инвазивно и не переписывай лишнее.

Что нужно от тебя:
1. Сначала быстро прочитай `README.md`, `src/reels_analyzer/cli.py` и структуру `src/reels_analyzer/`.
2. Потом кратко опиши текущее состояние проекта.
3. После этого помоги мне продолжить работу над следующей задачей: <вставь свою задачу здесь>.
```

Recommended reminder:

- mention the exact file you are working on now;
- mention whether you need base run or full run with Whisper/Ollama;
- mention active devcontainer profile: CPU (`devcontainer.cpu.json`) or GPU (`devcontainer.gpu.json`);
- if you already have a dataset, point to the exact path.
