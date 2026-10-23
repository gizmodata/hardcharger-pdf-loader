import pytest

from hardcharger_pdf_loader import HardchargerSettings


@pytest.fixture(autouse=True)
def clean_connection_env(monkeypatch):
    for name in (
        "HOSTNAME", "PORT", "USERNAME", "PASSWORD", "USE_TLS", "TLS_SKIP_VERIFY",
    ):
        monkeypatch.delenv(f"HARDCHARGER_{name}", raising=False)


def test_hostname_required(monkeypatch):
    monkeypatch.setenv("GIZMOSQL_HOSTNAME", "legacy.example.com")
    with pytest.raises(ValueError, match="HARDCHARGER_HOSTNAME"):
        HardchargerSettings.from_env()


def test_secure_defaults(monkeypatch):
    monkeypatch.setenv("HARDCHARGER_HOSTNAME", "db.example.com")
    settings = HardchargerSettings.from_env()
    assert settings.uri == "hardcharger://db.example.com:31337"
    assert settings.use_tls is True
    assert settings.tls_skip_verify is False


@pytest.mark.parametrize("value", ["false", "0", "off"])
def test_plain_http_configuration(monkeypatch, value):
    for key, val in {
        "HOSTNAME": "localhost", "PORT": "43123", "USERNAME": "loader",
        "PASSWORD": "p:a@ss", "USE_TLS": value, "TLS_SKIP_VERIFY": "yes",
    }.items():
        monkeypatch.setenv(f"HARDCHARGER_{key}", val)
    settings = HardchargerSettings.from_env()
    assert settings.uri == "hardcharger://localhost:43123?tls=false"
    assert settings.username == "loader"
    assert settings.password == "p:a@ss"
    assert settings.tls_skip_verify is True
