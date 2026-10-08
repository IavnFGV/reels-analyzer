# Video Script: Conversational RU

## Main voiceover

Dev Container пишет, что preflight прошел нормально. Ошибок нет. И потом просто тишина.

В такие моменты кажется, что завис `initializeCommand`. Но он уже закончился.

Настоящая проблема вообще в другом месте.

Смотри: если запустить обычный `docker build` с подробным логом, внезапно появляется строка `load build context`.

И вот там Docker может залипнуть надолго, потому что он сначала собирает и отправляет весь build context.

Если `context` указывает на широкую папку, а `.dockerignore` нет, в сборку начинает лететь все подряд.

Даже если твой Dockerfile выглядит маленьким и безобидным.

Вот почему после preflight может быть долгая пауза без явной ошибки.

Добавляешь `.dockerignore`, выкидываешь тяжелые папки из context, и загадочное зависание просто исчезает.

Короче: если Dev Container будто бы висит сразу после `initializeCommand`, смотри не только на скрипты. Очень часто тормозит именно `load build context`.

## Short punchy version

Preflight прошел.

Потом тишина.

Кажется, сломался `initializeCommand`.

Но нет.

Docker в этот момент пакует build context.

Без `.dockerignore` туда может улететь полпроекта.

Поэтому Dev Container выглядит зависшим, хотя проблема вообще не в скрипте.

## On-screen captions

- `Preflight passed`
- `Why is it frozen?`
- `False suspect: initializeCommand`
- `Real suspect: load build context`
- `No .dockerignore`
- `Huge context`
- `Tiny fix, big difference`

## Demo order

1. Open [broken](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/broken)
2. Show the pause after preflight
3. Run:

```bash
docker build -f .devcontainer/Dockerfile . --progress=plain
```

4. Highlight `load build context`
5. Open [fixed](/opt/projects/reels-analyzer/docs/devcontainer-context-mystery/fixed)
6. Show the same build becoming instant
