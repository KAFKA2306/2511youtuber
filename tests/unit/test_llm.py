import types

import pytest

pytestmark = pytest.mark.unit


class DummyResponse(types.SimpleNamespace):
    pass


def _dummy_completion_factory(record):
    def _completion(*args, **kwargs):
        record.append(kwargs.get("api_key"))
        return DummyResponse(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="dummy"))])

    return _completion
