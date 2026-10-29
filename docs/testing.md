# Test coverage

The port preserves every test function from upstream `gizmosql-pdf-loader` commit
`30cbe4d168ec0b0b3717cf431efcdc5442d9e5a5` (version 0.1.2): public exports,
deterministic document IDs, chunk streaming/reconstruction, page batching, DuckLake-safe
DDL, FTS plans, PDF dates/metadata/text, hidden layers, language-data resolution, OCR,
and live load/list/search/replace and BM25 stemming.

The live tests use `adbc-driver-hardcharger` over Chargewire against the released
Hardcharger 2.0.0 server. Each original live test now runs for both a persistent DuckDB
catalog and a DuckLake catalog. Missing language data or extensions fails the suite;
there are no prerequisite-based skips.

Additional coverage checks Hardcharger environment variables and secure URI defaults,
the actual load/list/search/index CLI, the downloadable Python example with byte-for-byte
and SHA-256 verification, recorded Hardcharger user identity, and cleanup of partially
uploaded data after an error. The CLI and error-cleanup tests run for both catalog types.

Validated locally on macOS arm64 on 2026-10-23:

| Python | Result |
|---|---|
| 3.11.15 | 42 passed, 0 skipped |
| 3.12.13 | 42 passed, 0 skipped |
| 3.13.12 | 42 passed, 0 skipped |
| 3.14.7 | 42 passed, 0 skipped |
| 3.15.1 | 42 passed, 0 skipped |

The built wheel was also installed into a separate Python 3.15 environment and tested
with the full suite. CI repeats the full suite on Ubuntu for Python 3.11–3.15 on every
push and pull request. PyMuPDF emits third-party deprecation warnings on these versions.

```sh
pip install -e '.[dev]'
ruff check src tests examples
pytest -q -ra
python -m build
python -m twine check --strict dist/*
```
