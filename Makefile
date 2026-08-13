.PHONY: test smoke clean

SCRIPTS := skills/remove-ai-marks/scripts
PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

test:
	$(PYTHON) -m pytest

smoke:
	@tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(PYTHON) $(SCRIPTS)/inspect_text.py tests/fixtures/sample_watermarked.txt >/dev/null 2>&1 || true; \
	$(PYTHON) $(SCRIPTS)/clean_text.py tests/fixtures/sample_watermarked.txt -o "$$tmpdir/wm.cleaned.txt" --stats >/dev/null; \
	$(PYTHON) $(SCRIPTS)/rewrite_text.py tests/fixtures/sample_watermarked.txt -o "$$tmpdir/prompt.txt"; \
	$(PYTHON) $(SCRIPTS)/inspect_file.py tests/fixtures/sample_ai.md --json >/dev/null 2>&1 || true; \
	$(PYTHON) $(SCRIPTS)/clean_file.py tests/fixtures/sample_ai.md -o "$$tmpdir/sample_ai.cleaned.md"; \
	$(PYTHON) $(SCRIPTS)/clean_file.py tests/fixtures/sample_ai.html -o "$$tmpdir/sample_ai.cleaned.html"; \
	$(PYTHON) $(SCRIPTS)/clean_file.py tests/fixtures/sample_meta.svg -o "$$tmpdir/sample_meta.cleaned.svg"; \
	echo "smoke ok"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .venv
