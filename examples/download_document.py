"""Download a loaded PDF back out of Hardcharger by streaming its chunks in order.

Reads one chunk at a time (8 MiB by default) over Warp SQL and verifies the SHA-256
recorded at load time.

Usage: python examples/download_document.py "parts-manual-2.pdf" /tmp/parts-manual-2.pdf
"""

import hashlib
import os
import sys

from dotenv import load_dotenv

from hardcharger_pdf_loader.config import HardchargerSettings
from hardcharger_pdf_loader.loader import qualified_schema

load_dotenv(dotenv_path=".env")

file_name, out_path = sys.argv[1], sys.argv[2]
catalog = os.environ["HARDCHARGER_CATALOG"]
schema = os.environ.get("HARDCHARGER_SCHEMA", "pdf_docs")
qs = qualified_schema(catalog, schema)

with HardchargerSettings.from_env().connect(catalog=catalog) as conn, conn.cursor() as cur:
    cur.execute(
        f"SELECT document_id::VARCHAR, file_size_bytes, sha256_hex, chunk_count "
        f"FROM {qs}.documents WHERE file_name = ?",
        parameters=[file_name],
    )
    document_id, file_size_bytes, sha256_hex, chunk_count = cur.fetchone()

    digest = hashlib.sha256()
    written = 0
    with open(out_path, "wb") as out:
        for chunk_index in range(chunk_count):
            cur.execute(
                f"SELECT content FROM {qs}.document_chunks WHERE document_id = ? AND chunk_index = ?",
                parameters=[document_id, chunk_index],
            )
            (content,) = cur.fetchone()
            out.write(content)
            digest.update(content)
            written += len(content)

print(f"wrote {written:,} of {file_size_bytes:,} bytes to {out_path}")
print("sha256 matches:", digest.hexdigest() == sha256_hex)
