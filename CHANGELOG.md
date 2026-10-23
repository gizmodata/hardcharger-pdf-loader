# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-23

### Added
- Hardcharger™ PDF Loader, adapted from GizmoSQL PDF Loader 0.1.2
  (upstream commit `30cbe4d168ec0b0b3717cf431efcdc5442d9e5a5`).
- `hardcharger-pdf-loader load|list|search|index` and `python -m hardcharger_pdf_loader`.
- Importable `hardcharger_pdf_loader` API with `HardchargerSettings`, `LoadOptions`, OCR,
  PDF metadata and page extraction, chunked byte uploads/downloads and BM25 full-text search.
- Native Hardcharger ADBC driver 2.0.2+ over Warp SQL, `hardcharger://` URIs, TLS by default
  and `?tls=false` for plain HTTP; `HARDCHARGER_*` environment configuration.
- All upstream test cases, with live coverage for both DuckDB and DuckLake, including
  replacement, byte-for-byte reconstruction, OCR and ranked search. Live tests start the
  released Hardcharger 2.0.0 server automatically and fail on missing prerequisites.
- Hardcharger light/dark branding, package/CI/license/protocol badges and runnable examples.
- Full-suite CI on Python 3.11–3.15, wheel/source builds, GitHub Releases and PyPI trusted
  publishing through the `pypi` environment in `ci.yml`.

### Changed
- Removed Flight SQL/gRPC connection settings and limits; uploads stream Arrow IPC over Warp SQL.
- Requires Python 3.11+ to match the released Hardcharger ADBC driver and PyArrow.
