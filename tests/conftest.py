"""Run live tests against an isolated Hardcharger server, or HARDCHARGER_PDF_LOADER_TEST_HOSTNAME.

The local server comes from the pinned development dependency and uses a temporary
DuckDB file, home directory and random credentials. Missing binaries/extensions fail.

The suite reads only HARDCHARGER_PDF_LOADER_TEST_* variables, never the loader's own
HARDCHARGER_* connection variables or a .env file: those may name a real server and its
credentials, which a test run must not reach (or write to). They are removed from the
environment for the run, so the CLI and from_env() tests see only what a test sets.
"""

import os

import pytest

from hardcharger_pdf_loader import HardchargerSettings

TEST_PREFIX = "HARDCHARGER_PDF_LOADER_TEST_"
CONNECTION_VARIABLES = (
    "HOSTNAME",
    "PORT",
    "USERNAME",
    "PASSWORD",
    "USE_TLS",
    "TLS_SKIP_VERIFY",
    "CATALOG",
    "SCHEMA",
)

for _name in CONNECTION_VARIABLES:
    os.environ.pop(f"HARDCHARGER_{_name}", None)


def _test_bool(name: str, default: bool) -> bool:
    value = os.environ.get(TEST_PREFIX + name)
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@pytest.fixture(scope="session")
def server_settings(tmp_path_factory):
    hostname = os.environ.get(TEST_PREFIX + "HOSTNAME")
    if hostname:
        yield HardchargerSettings(
            hostname=hostname,
            port=int(os.environ.get(TEST_PREFIX + "PORT", "31337")),
            username=os.environ.get(TEST_PREFIX + "USERNAME"),
            password=os.environ.get(TEST_PREFIX + "PASSWORD"),
            use_tls=_test_bool(name="USE_TLS", default=True),
            tls_skip_verify=_test_bool(name="TLS_SKIP_VERIFY", default=False),
        )
        return

    from hardcharger import Server

    workdir = tmp_path_factory.mktemp("hardcharger")
    with Server(
        database=workdir / "pdf_loader.duckdb",
        version="2.7.0",
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
