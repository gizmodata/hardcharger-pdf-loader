"""Run live tests against an isolated Hardcharger server, or HARDCHARGER_HOSTNAME.

The local server comes from the pinned development dependency and uses a temporary
DuckDB file, home directory and random credentials. Missing binaries/extensions fail.
"""

import os

import pytest
from dotenv import load_dotenv

from hardcharger_pdf_loader import HardchargerSettings

load_dotenv(dotenv_path=".env")


@pytest.fixture(scope="session")
def server_settings(tmp_path_factory):
    if os.environ.get("HARDCHARGER_HOSTNAME"):
        yield HardchargerSettings.from_env()
        return

    from hardcharger import Server

    workdir = tmp_path_factory.mktemp("hardcharger")
    with Server(
        database=workdir / "pdf_loader.duckdb",
        version="2.3.0",
        env={"HOME": str(workdir), "USERPROFILE": str(workdir)},
        log_file=workdir / "server.log",
    ) as server:
        settings = HardchargerSettings(
            hostname="127.0.0.1",
            port=server.port,
            username=server.username,
            password=server.password,
            use_tls=False,
        )
        with settings.connect() as conn, conn.cursor() as cur:
            cur.execute("ATTACH ':memory:' AS memory")
        yield settings
