# Integration tests conftest - override async fixtures to prevent event loop conflicts
import asyncio

import pytest


@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test function."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
