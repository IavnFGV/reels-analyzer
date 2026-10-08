PYTHON ?= python
PIP ?= pip
PYTHONPATH_VALUE ?= src

.PHONY: install install-dev help run resolve-channel

install:
	$(PIP) install -e .

install-dev:
	$(PIP) install -e ".[dev,video,transcription,llm]"

help:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON) -m reels_analyzer --help

run-help:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON) -m reels_analyzer run --help

run:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON) -m reels_analyzer run --channel $(CHANNEL) $(if $(LINKS),--links-file $(LINKS),) $(FLAGS)

resolve-channel:
	PYTHONPATH=$(PYTHONPATH_VALUE) $(PYTHON) scripts/resolve-tiktok-channel.py --channel $(CHANNEL) --output $(OUT) $(FLAGS)
