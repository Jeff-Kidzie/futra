"""
Pytest configuration for EA integration tests.

Makes the temp_ipc_dir fixture from test_helpers available to all
test modules in this directory.
"""
from tests.ea.test_helpers import temp_ipc_dir  # noqa: F401
