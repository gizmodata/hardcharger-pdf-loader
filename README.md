<p align="center">
  <a href="https://github.com/gizmodata/hardcharger">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/gizmodata/hardcharger-pdf-loader/main/docs/assets/hardcharger-banner-dark.png">
      <img src="https://raw.githubusercontent.com/gizmodata/hardcharger-pdf-loader/main/docs/assets/hardcharger-banner-light.png" alt="Hardcharger™" width="400">
    </picture>
  </a>
</p>

<h1 align="center">Hardcharger™ PDF Loader</h1>

<p align="center">
  <a href="https://github.com/gizmodata/hardcharger-pdf-loader/actions/workflows/ci.yml"><img src="https://github.com/gizmodata/hardcharger-pdf-loader/actions/workflows/ci.yml/badge.svg" alt="CI: full suite on Python 3.11–3.15"></a>
  <a href="https://pypi.org/project/hardcharger-pdf-loader/"><img src="https://img.shields.io/pypi/v/hardcharger-pdf-loader?logo=pypi" alt="PyPI version"></a>
  <a href="https://pypi.org/project/hardcharger-pdf-loader/"><img src="https://img.shields.io/badge/Python-3.11–3.15-3776AB?logo=python&amp;logoColor=white" alt="Python 3.11–3.15"></a>
  <a href="https://pypi.org/project/hardcharger-pdf-loader/"><img src="https://img.shields.io/pepy/dt/hardcharger-pdf-loader.svg" alt="PyPI downloads"></a>
  <a href="https://github.com/gizmodata/hardcharger-adbc"><img src="https://img.shields.io/badge/driver-Hardcharger%20ADBC-f15a24.svg" alt="Hardcharger ADBC driver"></a>
  <a href="https://github.com/gizmodata/chargewire"><img src="https://img.shields.io/badge/protocol-Chargewire-31a8db.svg" alt="Chargewire protocol"></a>
  <a href="https://github.com/gizmodata/hardcharger-pdf-loader/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-brightgreen.svg" alt="Apache 2.0 license"></a>
  <a href="https://gizmodata.com"><img src="https://img.shields.io/badge/by-GizmoData%E2%84%A2-f15a24.svg" alt="GizmoData™"></a>
</p>

Load PDF files into a [Hardcharger™](https://github.com/gizmodata/hardcharger) server over
[Chargewire](https://github.com/gizmodata/chargewire) / ADBC so SQL clients and
[Hardcharger MCP](https://github.com/gizmodata/hardcharger-mcp) agents can **search the text**
and **download the original files**.

Adapted from [gizmosql-pdf-loader](https://github.com/gizmodata/gizmosql-pdf-loader), with its
complete test suite ported to the Hardcharger server and `adbc-driver-hardcharger`.

For every PDF the loader stores:

| What | Where | Notes |
|---|---|---|
| File metadata | `documents` | name, path, MIME type, size, SHA-256, page count, PDF info (title, author, creator, producer, dates), encryption, optional-content layers, load stats |
| File bytes | `document_chunks` | fixed-size chunks (default 8 MiB), streamed as Arrow IPC over Chargewire |
| Page text | `document_pages` | one row per page, with page label, size, rotation, image count and how the text was obtained (`native`, `ocr`, `none`) |
| Whole text | `document_text` (view) | pages joined with form-feed characters |
| Search helpers | `search_pages(term)`, `search_pages_ranked(term, top_k)` (table macros) | case-insensitive substring search with a snippet; BM25-ranked full-text search (stemmed) |

Works with plain DuckDB catalogs and with **DuckLake** catalogs (no primary-key / unique constraints are used;
the loader de-duplicates on SHA-256 itself).

## Install

```shell
python3 -m venv .venv && . .venv/bin/activate
pip install hardcharger-pdf-loader          # or: pip install dist/hardcharger_pdf_loader-*.whl
```

Python **3.11–3.15**. Tested with Hardcharger server **2.3.0** and ADBC driver **2.1.0**.

Dependencies: `adbc-driver-hardcharger` (>= 2.0.2), `pyarrow`, `pymupdf`, `click`, `python-dotenv`.

OCR of image-only pages needs no extra install: the Tesseract engine ships inside the PyMuPDF wheel, and the
only external piece, the trained language data (`eng.traineddata`, about 4 MB), is downloaded on first use into
`~/.cache/hardcharger-pdf-loader/tessdata` from the [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast)
repository. An installed Tesseract's language folder (or `--tessdata` / `TESSDATA_PREFIX`) is used instead when
present; `--no-ocr-download` forbids the download. Without language data, image-only pages are loaded with empty
text and a warning.

## Configure

Create a `.env` in the working directory (or export the variables):

```dotenv
HARDCHARGER_HOSTNAME=hardcharger.example.com
HARDCHARGER_PORT=443
HARDCHARGER_USERNAME=me@example.com
HARDCHARGER_PASSWORD=...
HARDCHARGER_CATALOG=my_lake          # target catalog (must already be attached on the server)
HARDCHARGER_SCHEMA=pdf_docs          # target schema (created if missing); default: pdf_docs
# optional
HARDCHARGER_USE_TLS=true             # false -> hardcharger://host:port?tls=false
HARDCHARGER_TLS_SKIP_VERIFY=false
```

Set the catalog explicitly. A session's default catalog is whatever database the server was started with,
which on some deployments is the ephemeral in-memory `memory` catalog; the loader refuses to load into `memory`
or `temp` so tables can't silently land somewhere that vanishes on restart.

## Use

```shell
# Load every *.pdf in a directory (or pass explicit file paths)
hardcharger-pdf-loader load --source-dir source_pdf_files

# Inspect/extract without connecting to the server
hardcharger-pdf-loader load --dry-run --source-dir source_pdf_files

# What is loaded?
hardcharger-pdf-loader list

# Search page text: substring match, or BM25-ranked via the full-text index
hardcharger-pdf-loader search "hydraulic pump" --limit 5
hardcharger-pdf-loader search "hydraulic pump relief valves" --ranked --limit 5

# (Re)build the full-text index (also done automatically at the end of `load`)
hardcharger-pdf-loader index
```

Useful `load` options (see `hardcharger-pdf-loader load --help` for all):

| Option | Default | Purpose |
|---|---|---|
| `--chunk-size-mib N` | 8 | Size of each stored chunk, streamed in an Arrow IPC record batch |
| `--replace` | off | Reload documents whose SHA-256 is already present (otherwise they are skipped) |
| `--ocr/--no-ocr`, `--ocr-language`, `--ocr-dpi`, `--ocr-workers` | on, `eng`, 200, CPUs-1 | OCR of pages that have images but no text (`eng+jpn` style multi-language works if each file is available) |
| `--tessdata DIR`, `--ocr-download/--no-ocr-download` | auto, on | Where Tesseract language data comes from (see Install) |
| `--reveal-hidden-layers` | off | See [Hidden layers](#hidden-layers-secure-pdfs) |
| `--max-pages N` | all | Only extract the first N pages (testing) |
| `--dry-run` | off | Extract locally, print a summary, upload nothing |
| `--fts-index/--no-fts-index` | on | Rebuild the full-text index after loading; built in place for a DuckDB-file target, skipped for a DuckLake target unless `--fts-catalog` is given |
| `--fts-catalog`, `--fts-schema` | none, `pdf_fts` | DuckDB catalog (and schema) to hold a copy-based index when the target is a DuckLake (see below) |

Documents are identified by a UUID derived from the file's SHA-256, so the same bytes always map to the same
`document_id`; re-running the loader is idempotent.

## Use as a Python library

Everything the CLI does is a plain function call; the top-level package exports the pieces you need
(`HardchargerSettings`, `LoadOptions`, `OcrSettings`, `ensure_schema`, `load_pdf`, `plan_fts`, `build_fts_index`,
`inspect_pdf`, `extract_pages`, ...). `examples/load_with_python.py` is the runnable version of this:

```python
import sys
from pathlib import Path

from dotenv import load_dotenv

from hardcharger_pdf_loader import (
    HardchargerSettings,
    LoadOptions,
    OcrSettings,
    build_fts_index,
    ensure_schema,
    load_pdf,
    plan_fts,
)

load_dotenv(dotenv_path=".env")

CATALOG = "my_lake"
SCHEMA = "pdf_docs"
source_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "source_pdf_files")

# HardchargerSettings(hostname=..., port=..., username=..., password=...) also works without env vars.
settings = HardchargerSettings.from_env()

with settings.connect(catalog=CATALOG) as conn:
    ensure_schema(conn, catalog=CATALOG, schema=SCHEMA)  # idempotent: tables, views, macros, migrations

    options = LoadOptions(
        catalog=CATALOG,
        schema=SCHEMA,
        chunk_size=8 * 1024 * 1024,
        replace=False,  # True reloads files whose SHA-256 is already present
        ocr=OcrSettings(enabled=True, language="eng"),
    )
    for pdf_path in sorted(source_dir.glob("*.pdf")):
        result = load_pdf(conn, path=pdf_path, options=options)
        r = result
        print(f"{r.status:8} {r.file_name}: {r.page_count} pages, {r.total_text_chars:,} chars")

    # Full-text index: built in place on a DuckDB-file catalog, skipped on DuckLake unless a
    # DuckDB catalog is named to hold a copy of the page text.
    plan = plan_fts(conn, catalog=CATALOG, schema=SCHEMA, fts_catalog="memory")
    print(f"fts: {plan.mode} ({plan.reason})")
    pages_indexed = build_fts_index(conn, plan)

    with conn.cursor() as cur:
        if pages_indexed:
            cur.execute(
                f"SELECT file_name, page_number, score "
                f"FROM {CATALOG}.{SCHEMA}.search_pages_ranked(?, top_k := 3)",
                parameters=["relief valve"],
            )
        else:
            cur.execute(
                f"SELECT file_name, page_number, snippet FROM {CATALOG}.{SCHEMA}.search_pages(?) LIMIT 3",
                parameters=["relief valve"],
            )
        for row in cur.fetchall():
            print(row)
```

`load_pdf` returns a `LoadResult` (`status` is `"loaded"` or `"skipped"`, plus chunk/page/text counts and the
`document_id`). `inspect_pdf(path)` and `extract_pages(path, ocr=...)` work without any server connection if
you only want the metadata or the text.

## Query from SQL

```sql
-- Ranked full-text search (BM25, English stemming) via the fts index
SELECT file_name, page_number, score, snippet
  FROM my_lake.pdf_docs.search_pages_ranked('hydraulic pump relief valves', top_k := 10);

-- Ranked search by hand: call the index's match_bm25 macro directly. The index schema is
-- fts_<schema>_document_pages in the catalog that holds the indexed table: the target catalog
-- for a DuckDB-file target (below), or the --fts-catalog for a DuckLake target, e.g.
-- memory.fts_pdf_fts_document_pages over memory.pdf_fts.document_pages.
-- conjunctive := 1 requires every term on the page (default: any term, ranked).
SELECT d.file_name, p.page_number, round(p.score, 2) AS score
  FROM (SELECT document_id, page_number,
               my_db.fts_pdf_docs_document_pages.match_bm25(page_id, 'hydraulic relief valve', conjunctive := 1) AS score
          FROM my_db.pdf_docs.document_pages) p
  JOIN my_db.pdf_docs.documents d USING (document_id)
 WHERE p.score IS NOT NULL
 ORDER BY p.score DESC
 LIMIT 10;

-- Substring search with a snippet (case-insensitive, no index needed)
SELECT file_name, page_number, snippet
  FROM my_lake.pdf_docs.search_pages('relief valve')
 LIMIT 10;

-- Same thing by hand
SELECT d.file_name, p.page_number, p.page_text
  FROM my_lake.pdf_docs.document_pages p
  JOIN my_lake.pdf_docs.documents d USING (document_id)
 WHERE p.page_text ILIKE '%relief valve%';

-- Metadata
SELECT file_name, mime_type, file_size_bytes, page_count, pages_with_text, title, producer, pdf_created_at
  FROM my_lake.pdf_docs.documents;

-- Fetch a file's chunks in order (each row is one chunk, so any client message limit works)
SELECT chunk_index, content
  FROM my_lake.pdf_docs.document_chunks
 WHERE document_id = (SELECT document_id FROM my_lake.pdf_docs.documents
                       WHERE file_name = 'parts-manual-2.pdf')
 ORDER BY chunk_index;
```

### Full-text index

`search_pages_ranked` is backed by DuckDB's [`fts`](https://duckdb.org/docs/stable/core_extensions/full_text_search)
extension (BM25 scoring, English stemmer). The loader looks up the target catalog's type in `duckdb_databases()`
and logs what it decides:

| Target catalog type | What happens |
|---|---|
| `duckdb` (a DuckDB database file) | The index is built **in place** on `document_pages` and persists with the file. `search_pages_ranked` is created next to the tables. |
| `ducklake` | **Skipped**, with the reason logged: an FTS index cannot be created inside a DuckLake catalog (the extension's internal tables use a NULL-typed column DuckLake rejects: "unsupported type NULL"). |
| `ducklake` + `--fts-catalog <duckdb catalog>` | The page text is **copied** into `<fts-catalog>.<fts-schema>.document_pages` (a few MB for these manuals), the index is built there in under a second, and `search_pages_ranked` in the target schema points at it. |

Loading the `fts` extension needs the Hardcharger **admin** role; *querying* an existing index does not. The
index is a snapshot: `load` refreshes it after loading new documents, and `hardcharger-pdf-loader index` rebuilds
it on demand. If the copy catalog is the server's in-memory `memory` catalog (as in the example below), the copy
and index vanish on a server restart, so run `index` again afterwards (or point `--fts-catalog` at an attached DuckDB file).

```shell
# DuckLake target: opt in to a copy-based index in the shared in-memory catalog
hardcharger-pdf-loader index --fts-catalog memory
```

## Download a file from Python

`examples/download_document.py` streams the chunks in order and verifies the SHA-256
without buffering the whole PDF:

```shell
python examples/download_document.py "parts-manual-2.pdf" /tmp/parts-manual-2.pdf
```

The core of it:

```python
cur.execute(
    f"SELECT content FROM {qs}.document_chunks WHERE document_id = ? AND chunk_index = ?",
    parameters=[document_id, chunk_index],
)
(content,) = cur.fetchone()
out.write(content)
```

## Hidden layers ("secure" PDFs)

Some vendor products (e.g. HyperGEAR PDFLib "secure documents") do not encrypt a PDF; they put the real
content on an optional-content layer whose default view state is OFF and rely on viewer JavaScript to switch it
on after checking a license window. Outside that viewer every page looks blank, and OCR finds nothing.

The loader records such layers in `documents.hidden_layer_names` and, by default, leaves them alone. With
`--reveal-hidden-layers` it writes a temporary copy with those layers switched ON, extracts text from the copy,
deletes it, and sets `documents.hidden_layers_revealed = true`. The stored file bytes are always the original.
Use this only for documents you are entitled to read outside the vendor's viewer.

## Streaming file bytes

Uploads use `cursor.adbc_ingest` with a `RecordBatchReader`, one record batch per chunk
(8 MiB by default), over Chargewire's Arrow IPC transport. Page text is sent in batches of
200 pages. Downloads read the chunks in `chunk_index` order and verify the SHA-256.

There is no server-side view that concatenates a whole file: large BLOB concatenations can
use much more memory than the original PDF. Reassemble on the client with
`examples/download_document.py`.

## Development

```shell
pip install -e ".[dev]"
ruff check src tests examples
pytest -q -ra                 # every test, including OCR + live DuckDB and DuckLake integration
python -m build                # wheel + sdist in dist/
```

The suite starts an isolated **Hardcharger 2.3.0** subprocess automatically using the
`hardcharger==2.3.0` development dependency. The server binary is downloaded and verified
on first use. Each run uses a temporary DuckDB file, a temporary home and random credentials.
OCR language data and the DuckDB `fts` / `ducklake` extensions are downloaded when needed;
missing prerequisites fail tests instead of skipping them. To use your own server instead,
set `HARDCHARGER_HOSTNAME` and the connection variables above (administrator access and a
persistent catalog are required; attach a DuckDB catalog named `memory` for the copy-index test).
`pytest -m "not integration"` runs only the tests that do not need a server.

CI runs the full suite on **Python 3.11, 3.12, 3.13, 3.14 and 3.15**, then builds and checks
both the wheel and source distribution.

Releases: bump `version` in `pyproject.toml`, move the `[Unreleased]` notes in `CHANGELOG.md` into a version
section, commit, then `git push origin main vX.Y.Z`. CI runs the tests on Python 3.11 through 3.15, builds the
wheel and sdist, creates a GitHub Release with that CHANGELOG section as the notes and the artifacts attached,
and publishes the package to PyPI via
[trusted publishing](https://docs.pypi.org/trusted-publishers/) (the `pypi` GitHub environment; no token
secrets).


Exact PyPI publisher values and first-release steps are in [docs/publishing.md](docs/publishing.md).

---

<p align="center">
  <a href="https://gizmodata.com"><img src="https://raw.githubusercontent.com/gizmodata/hardcharger-pdf-loader/main/docs/assets/gizmodata-logo.png" alt="GizmoData™" width="56"></a><br>
  <sub>Built by <a href="https://gizmodata.com">GizmoData™</a></sub>
</p>
<p align="center"><sub>Hardcharger™ and GizmoData™ are trademarks of GizmoData LLC.</sub></p>
