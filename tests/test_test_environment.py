"""The suite never sees the loader's own connection variables (see conftest.py)."""

import os

from conftest import CONNECTION_VARIABLES


def test_the_loaders_connection_variables_are_not_in_the_test_environment():
    leaked = [f"HARDCHARGER_{name}" for name in CONNECTION_VARIABLES if f"HARDCHARGER_{name}" in os.environ]
    assert leaked == [], f"a real server's settings reached the test run: {leaked}"
