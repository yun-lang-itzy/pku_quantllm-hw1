.PHONY: check test

check:
	python3 scripts/wiki_lint.py

test:
	python3 -m unittest discover -s experiments/002-ctp-demo -p 'test_*.py' -v
