"""Connection settings for the target Hardcharger server."""

from __future__ import annotations

import os
from dataclasses import dataclass

from adbc_driver_hardcharger import dbapi as hardcharger

EPHEMERAL_CATALOGS = frozenset({"memory", "temp"})


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass
class HardchargerSettings:
    hostname: str
    port: int = 31337
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    tls_skip_verify: bool = False

    @classmethod
    def from_env(cls) -> HardchargerSettings:
        hostname = os.environ.get("HARDCHARGER_HOSTNAME")
        if not hostname:
            raise ValueError("HARDCHARGER_HOSTNAME is not set (put it in .env or the environment)")
        return cls(
            hostname=hostname,
            port=int(os.environ.get("HARDCHARGER_PORT", "31337")),
            username=os.environ.get("HARDCHARGER_USERNAME"),
            password=os.environ.get("HARDCHARGER_PASSWORD"),
            use_tls=_env_bool(name="HARDCHARGER_USE_TLS", default=True),
            tls_skip_verify=_env_bool(name="HARDCHARGER_TLS_SKIP_VERIFY", default=False),
        )

    @property
    def uri(self) -> str:
        uri = f"hardcharger://{self.hostname}:{self.port}"
        if not self.use_tls:
            uri += "?tls=false"
        return uri

    def connect(self, *, catalog: str | None = None, db_schema: str | None = None) -> hardcharger.Connection:
        """Open a DBAPI connection over Chargewire.

        ``catalog`` becomes the session's current catalog. It must already be attached on the
        server (attaching requires the Hardcharger admin role).
        """
        return hardcharger.connect(
            uri=self.uri,
            username=self.username,
            password=self.password,
            tls_skip_verify=self.tls_skip_verify,
            catalog=catalog,
            db_schema=db_schema,
        )


def resolve_target_catalog(conn: hardcharger.Connection, catalog: str | None) -> str:
    """Return the catalog to load into, refusing the server's ephemeral in-memory catalogs.

    A session's default catalog is whatever database the server was started with; on some
    deployments that is the in-memory ``memory`` catalog, and loading there without noticing
    would put every table somewhere that vanishes on restart.
    """
    if catalog:
        return catalog
    with conn.cursor() as cur:
        cur.execute("SELECT current_catalog()")
        current = cur.fetchone()[0]
    if current in EPHEMERAL_CATALOGS:
        raise ValueError(
            f"The session's default catalog on this server is the ephemeral '{current}' catalog. "
            "Pass --catalog (or set HARDCHARGER_CATALOG) to name a persistent catalog."
        )
    return current
