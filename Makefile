PYTHON ?= python3
.PHONY: test validate browser-test preview

test:
	$(PYTHON) -m pytest -q tests
validate:
	$(PYTHON) tools/validate.py --report validation/local-checks.json
browser-test:
	$(PYTHON) tools/browser_smoke.py
preview:
	$(PYTHON) tools/preview.py
