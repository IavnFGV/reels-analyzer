# Video Script: Technical

## 0-3 sec

Dev Container прошел preflight. Ошибок нет. А потом просто завис.

## 3-6 sec

Лог намекает, что проблема в `initializeCommand`.

## 6-9 sec

Но это ложный след. Скрипт уже завершился.

## 9-13 sec

Show the `broken` demo stopping after:

`Host preflight passed. Next step should be fast... or should it?`

Voice:

Вот этот момент. Минутная тишина. Как будто VS Code умер.

## 13-17 sec

Show:

```bash
docker build -f .devcontainer/Dockerfile . --progress=plain
```

Voice:

Включаем нормальный лог Docker и смотрим, что реально происходит.

## 17-22 sec

Show:

`load build context`

`transferring context: 33.56MB`

Voice:

Вот виновник. Не preflight. Не Dockerfile-команды. Docker просто пакует build context.

## 22-27 sec

Show [broken/.devcontainer/devcontainer.json](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/broken/.devcontainer/devcontainer.json)

Voice:

`context` смотрит на всю папку проекта.

## 27-31 sec

Show that `broken` has no `.dockerignore`.

Voice:

А `.dockerignore` нет. Значит в сборку улетает все лишнее.

## 31-35 sec

Show [fixed/.dockerignore](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/fixed/.dockerignore)

Voice:

Добавляем одну маленькую вещь: `.dockerignore`.

## 35-40 sec

Show repeated build:

`load build context`

`transferring context: 378B`

Voice:

И все. Context стал крошечным. Пауза исчезла.

## 40-45 sec

Final:

Если Dev Container висит после `initializeCommand`, проверь `load build context`. Очень часто проблема именно там.

## On-screen text

- `Preflight passed`
- `Then... silence`
- `False clue`
- `Real culprit: load build context`
- `No .dockerignore = huge context`
- `378B instead of megabytes`

## Recording commands

```bash
bash docs/devcontainer-context-mystery/create-demo-payload.sh 512
```

```bash
docker build -f .devcontainer/Dockerfile . --progress=plain
```

Run `broken` from:

[broken](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/broken)

Run `fixed` from:

[fixed](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/fixed)
