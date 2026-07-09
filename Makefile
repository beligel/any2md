.PHONY: install test run gui build clean docker

install:
	bash install.sh

test:
	. .venv/bin/activate && pytest -q

run:
	. .venv/bin/activate && python any2md_gui.py

gui:
	$(MAKE) run

cli:
	. .venv/bin/activate && any2md --help

build:
	. .venv/bin/activate && python -m build

clean:
	rm -rf build dist *.egg-info __pycache__ .pytest_cache

docker:
	docker build -t any2md:latest .
