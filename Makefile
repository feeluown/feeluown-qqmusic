.PHONY: docs

all: test

lint:
	flake8 --max-line-length=89 fuo_qqmusic/

unittest: pytest

pytest:
	pytest --cov-report= --cov=fuo_qqmusic
	pytest tests/

test: lint pytest

clean:
	find . -name "*~" -exec rm -f {} \;
	find . -name "*.pyc" -exec rm -f {} \;
	find . -name "*flymake.py" -exec rm -f {} \;
	find . -name "\#*.py\#" -exec rm -f {} \;
	find . -name ".\#*.py\#" -exec rm -f {} \;
	find . -name __pycache__ -delete
