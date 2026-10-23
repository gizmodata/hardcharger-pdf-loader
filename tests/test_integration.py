"""End-to-end test against a real Hardcharger server.

Runs against a temporary local server by default, or HARDCHARGER_HOSTNAME.
Loads into throw-away schemas in both DuckDB and DuckLake catalogs, then drops them.
"""

import os
import uuid
from pathlib import Path

import pymupdf
import pytest

from hardcharger_pdf_loader.loader import qualified_schema

pytestmark = pytest.mark.integration


@pytest.fixture
def pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "integration.pdf"
    doc = pymupdf.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), f"Integration page {i + 1}. The swing motor relief valve.")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture(params=["duckdb", "ducklake"])
def scratch_schema(request, server_settings, tmp_path):
    from hardcharger_pdf_loader.config import resolve_target_catalog

    schema = f"pdf_loader_test_{uuid.uuid4().hex[:8]}"
    with server_settings.connect(catalog=os.environ.get("HARDCHARGER_CATALOG")) as conn:
        catalog = resolve_target_catalog(conn, os.environ.get("HARDCHARGER_CATALOG"))
        if request.param == "ducklake":
            catalog = f"lake_{uuid.uuid4().hex[:8]}"
            metadata_path = (tmp_path / "metadata.ducklake").as_posix().replace("'", "''")
            with conn.cursor() as cur:
                cur.execute("INSTALL ducklake")
                cur.execute("LOAD ducklake")
                cur.execute(f"ATTACH 'ducklake:{metadata_path}' AS {catalog}")
        try:
            yield conn, catalog, schema
        finally:
            with conn.cursor() as cur:
                cur.execute(f"DROP SCHEMA IF EXISTS {qualified_schema(catalog, schema)} CASCADE")
                if request.param == "ducklake":
                    cur.execute(f"DETACH {catalog}")


def test_load_list_search_replace(pdf_path: Path, scratch_schema):
    from hardcharger_pdf_loader.loader import LoadOptions, ensure_schema, load_pdf

    conn, catalog, schema = scratch_schema
    ensure_schema(conn, schema=schema, catalog=catalog)
    qs = qualified_schema(catalog, schema)
    # tiny chunks to exercise multi-chunk streaming
    options = LoadOptions(schema=schema, catalog=catalog, chunk_size=1024)

    result = load_pdf(conn, path=pdf_path, options=options)
    assert result.status == "loaded"
    assert result.chunk_count > 1
    assert result.page_count == 5
    assert result.pages_with_text == 5

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT content FROM {qs}.document_chunks WHERE document_id = ? ORDER BY chunk_index",
            parameters=[result.document_id],
        )
        reassembled = b"".join(row[0] for row in cur.fetchall())
        assert reassembled == pdf_path.read_bytes()
        cur.execute(f"SELECT count(*) FROM {qs}.search_pages(?)", parameters=["relief VALVE"])
        assert cur.fetchone()[0] == 5
        cur.execute(f"SELECT page_count, mime_type, document_id::VARCHAR FROM {qs}.documents")
        page_count, mime_type, document_id = cur.fetchone()
        assert (page_count, mime_type, document_id) == (5, "application/pdf", result.document_id)

    # Second load of identical bytes is skipped; --replace reloads without duplicating rows.
    assert load_pdf(conn, path=pdf_path, options=options).status == "skipped"
    options.replace = True
    assert load_pdf(conn, path=pdf_path, options=options).status == "loaded"
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {qs}.documents")
        assert cur.fetchone()[0] == 1
        cur.execute(f"SELECT count(*) FROM {qs}.document_pages")
        assert cur.fetchone()[0] == 5


def test_fts_plan_and_ranked_search(pdf_path: Path, scratch_schema):
    """On a DuckDB-file target the index is built in place; on DuckLake it is skipped unless a
    DuckDB copy catalog is named. Both paths end in a working ranked search."""
    from hardcharger_pdf_loader.fts import (
        MODE_COPY,
        MODE_IN_CATALOG,
        MODE_SKIP,
        build_fts_index,
        plan_fts,
    )
    from hardcharger_pdf_loader.loader import LoadOptions, catalog_type, ensure_schema, load_pdf

    conn, catalog, schema = scratch_schema
    ensure_schema(conn, schema=schema, catalog=catalog)
    load_pdf(conn, path=pdf_path, options=LoadOptions(schema=schema, catalog=catalog))

    plan = plan_fts(conn, catalog=catalog, schema=schema)
    if catalog_type(conn, catalog) == "duckdb":
        assert plan.mode == MODE_IN_CATALOG
    else:
        assert plan.mode == MODE_SKIP
        assert build_fts_index(conn, plan) == 0
        plan = plan_fts(
            conn, catalog=catalog, schema=schema, fts_catalog="memory", fts_schema=f"{schema}_fts"
        )
        assert plan.mode == MODE_COPY
    indexed = build_fts_index(conn, plan)
    try:
        assert indexed == 5
        qs = qualified_schema(catalog, schema)
        with conn.cursor() as cur:
            # "valves" must match "valve" through stemming; results carry a score.
            cur.execute(
                f"SELECT page_number, score FROM {qs}.search_pages_ranked(?, top_k := ?)",
                parameters=["valves", 3],
            )
            rows = cur.fetchall()
        assert len(rows) == 3
        assert all(score > 0 for _, score in rows)
    finally:
        with conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA IF EXISTS {plan.index_schema} CASCADE")
            if plan.mode == MODE_COPY:
                cur.execute(f"DROP SCHEMA IF EXISTS {plan.fts_catalog}.{plan.fts_schema} CASCADE")


def test_cli_and_download_example(pdf_path, scratch_schema, server_settings, tmp_path):
    import subprocess
    import sys

    from click.testing import CliRunner

    from hardcharger_pdf_loader.cli import main
    from hardcharger_pdf_loader.loader import catalog_type

    conn, catalog, schema = scratch_schema
    fts_schema = f"{schema}_cli_fts"
    env = {
        "HARDCHARGER_HOSTNAME": server_settings.hostname,
        "HARDCHARGER_PORT": str(server_settings.port),
        "HARDCHARGER_USERNAME": server_settings.username or "",
        "HARDCHARGER_PASSWORD": server_settings.password or "",
        "HARDCHARGER_USE_TLS": str(server_settings.use_tls),
        "HARDCHARGER_TLS_SKIP_VERIFY": str(server_settings.tls_skip_verify),
        "HARDCHARGER_CATALOG": catalog,
        "HARDCHARGER_SCHEMA": schema,
    }
    runner = CliRunner()
    common = ["--catalog", catalog, "--schema", schema]
    fts = ["--fts-schema", fts_schema]
    copy_mode = catalog_type(conn, catalog) != "duckdb"
    if copy_mode:
        fts += ["--fts-catalog", "memory"]

    def invoke(args):
        result = runner.invoke(main, ["--env-file", str(tmp_path / "absent.env"), *args], env=env)
        assert result.exit_code == 0, f"{result.output}\n{result.exception}"
        return result.output

    try:
        assert "loaded" in invoke(["load", str(pdf_path), "--no-ocr", *common, *fts])
        assert "skipped" in invoke(["load", str(pdf_path), "--no-ocr", *common, *fts])
        assert "integration.pdf" in invoke(["list", *common])
        assert "5 hit(s)" in invoke(["search", "relief valve", *common])
        assert "3 hit(s)" in invoke(["search", "valves", "--ranked", "--limit", "3", *common])
        assert "rebuilt" in invoke(["index", *common, *fts])
        assert "loaded" in invoke(["load", str(pdf_path), "--replace", "--no-ocr", *common, *fts])

        output = tmp_path / "downloaded.pdf"
        example = Path(__file__).resolve().parents[1] / "examples" / "download_document.py"
        result = subprocess.run(
            [sys.executable, str(example), pdf_path.name, str(output)],
            env={**os.environ, **env}, capture_output=True, text=True, check=True,
        )
        assert "sha256 matches: True" in result.stdout
        assert output.read_bytes() == pdf_path.read_bytes()
        with conn.cursor() as cur:
            cur.execute(f"SELECT loaded_by FROM {qualified_schema(catalog, schema)}.documents")
            assert cur.fetchone()[0] == server_settings.username
    finally:
        with conn.cursor() as cur:
            index_catalog, index_schema = ("memory", fts_schema) if copy_mode else (catalog, schema)
            cur.execute(f"DROP SCHEMA IF EXISTS {index_catalog}.fts_{index_schema}_document_pages CASCADE")
            if copy_mode:
                cur.execute(f"DROP SCHEMA IF EXISTS memory.{fts_schema} CASCADE")


def test_partial_load_is_cleaned_up(pdf_path, scratch_schema, monkeypatch):
    from hardcharger_pdf_loader import loader

    conn, catalog, schema = scratch_schema
    loader.ensure_schema(conn, catalog=catalog, schema=schema)

    def fail_metadata(*args, **kwargs):
        raise RuntimeError("simulated metadata failure after uploading bytes and pages")

    monkeypatch.setattr(loader, "documents_batch", fail_metadata)
    with pytest.raises(RuntimeError, match="simulated metadata failure"):
        loader.load_pdf(conn, path=pdf_path, options=loader.LoadOptions(catalog=catalog, schema=schema))
    with conn.cursor() as cur:
        for table in ("documents", "document_chunks", "document_pages"):
            cur.execute(f"SELECT count(*) FROM {qualified_schema(catalog, schema)}.{table}")
            assert cur.fetchone()[0] == 0
