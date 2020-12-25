# type: ignore

import asynctest
import pytest
from fastapi.testclient import TestClient

from .main import DomainService, FooResult, HttpFooReq, app


@pytest.fixture(scope='module')
def client() -> TestClient:
    return TestClient(app)


@asynctest.patch.object(DomainService, 'foo')
def test_foo(mock_foo, client) -> None:
    request = HttpFooReq(x=True)

    # 500
    mock_foo.return_value = FooResult(error=FooResult.ErrorCode.EXISTS)
    response = client.post('/foo', data=request.json())
    assert response.status_code == 500

    # 422
    mock_foo.return_value = FooResult(error=FooResult.ErrorCode.ALREADY_UPDATED)
    response = client.post('/foo', data=request.json())
    assert response.status_code == 422

    # 200
    mock_foo.return_value = FooResult(x=True)
    response = client.post('/foo', data=request.json())
    assert response.status_code == 200
