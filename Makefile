.PHONY: docs

all: test

lint:
	flake8 fuo_qqmusic/

unittest: pytest

pytest:
	pytest --cov-report= --cov=fuo_qqmusic

test: lint

clean:
	find . -name "*~" -exec rm -f {} \;
	find . -name "*.pyc" -exec rm -f {} \;
	find . -name "*flymake.py" -exec rm -f {} \;
	find . -name "\#*.py\#" -exec rm -f {} \;
	find . -name ".\#*.py\#" -exec rm -f {} \;
	find . -name __pycache__ -delete
