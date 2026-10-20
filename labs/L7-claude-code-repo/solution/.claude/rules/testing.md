---
paths:
  - "tests/**/*.py"
---

# Test conventions

- Test files are named `test_l7_<topic>.py`, so they don't clash with other labs in one pytest run.
- Assert floats with `pytest.approx`.
- Use the real files in `data/`; don't mock the loader and don't add new fixture files.
- Test the CLI through `main([...])` with `capsys`, not with a subprocess.
