import datetime as dt
import logging
import random
from decimal import Decimal
from enum import Enum
from io import StringIO
from typing import Any, Dict, List, Optional, Union

import click
import orjson
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from ruamel.yaml import YAML
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def default(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.dict()
    if isinstance(obj, Decimal):
        return float(str(obj))
    if isinstance(obj, dt.datetime):
        if not obj.tzinfo:
            return obj.strftime('%Y-%m-%dT%H:%M:%S.%f+00:00')
        else:
            return obj.isoformat()
    if isinstance(obj, dt.time):
        return obj.strftime('%H:%M')
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    raise TypeError


class MyORJSONResponse(JSONResponse):
    media_type = 'application/json'

    def render(self, content: Any) -> bytes:
        return orjson.dumps(content, option=orjson.OPT_PASSTHROUGH_DATETIME, default=default)


def get_error(error_responses: Dict[Union[int, str], Dict[str, Any]], status: int, error_code: str) -> MyORJSONResponse:
    return MyORJSONResponse(status_code=status, content=error_responses[status]['model'](code=error_code).dict())


class StrEnum(str, Enum):
    def __str__(self) -> Any:
        return self.value


class ErrorCode(StrEnum):
    ALREADY_UPDATED = 'already_updated'
    CLIENT_NOT_FOUND = 'client_not_found'
    EXISTS = 'exists'
    UNKNOWN = 'unknown'
    INVALID_REQUEST = 'invalid_request'


class UnknownError(BaseModel):
    """
    http 500
    """

    class ErrorCode(StrEnum):
        UNKNOWN = ErrorCode.UNKNOWN

    code: ErrorCode


class InvalidRequestError(BaseModel):
    """
    http 400
    """

    class ErrorCode(StrEnum):
        INVALID_REQUEST = ErrorCode.INVALID_REQUEST

    code: ErrorCode
    details: List[Dict[str, Any]]


class BusinessError(BaseModel):
    """
    http 422
    """

    class ErrorCode(StrEnum):
        pass

    code: ErrorCode


# Foo
class FooResult(BaseModel):
    class ErrorCode(Enum):
        ALREADY_UPDATED = ErrorCode.ALREADY_UPDATED
        CLIENT_NOT_FOUND = ErrorCode.CLIENT_NOT_FOUND
        EXISTS = ErrorCode.EXISTS

    error: Optional[ErrorCode]
    x: Optional[bool]


class HttpFooError(BaseModel):
    """
    http 422
    """

    class ErrorCode(StrEnum):
        ALREADY_UPDATED = ErrorCode.ALREADY_UPDATED
        CLIENT_NOT_FOUND = ErrorCode.CLIENT_NOT_FOUND

    code: ErrorCode


http_foo_responses: Dict[Union[int, str], Dict[str, Any]] = {
    400: {'model': InvalidRequestError},
    422: {'model': HttpFooError},
    500: {'model': UnknownError},
}


class HttpFooReq(BaseModel):
    x: bool


class HttpFooResp(BaseModel):
    result: bool


# domain logic
class DomainService:
    @classmethod
    def foo(cls, x: bool) -> FooResult:
        result = [
            FooResult(error=FooResult.ErrorCode.CLIENT_NOT_FOUND),
            FooResult(error=FooResult.ErrorCode.ALREADY_UPDATED),
            FooResult(error=FooResult.ErrorCode.EXISTS),
            FooResult(x=x),
        ]
        return random.choice(result)


# http
DOMAIN_ERROR_TO_HTTP_ERROR_MAP = {
    FooResult.ErrorCode.CLIENT_NOT_FOUND: HttpFooError.ErrorCode.CLIENT_NOT_FOUND,
    FooResult.ErrorCode.ALREADY_UPDATED: HttpFooError.ErrorCode.ALREADY_UPDATED,
}

app = FastAPI()


@app.post("/foo", response_model=HttpFooResp, responses=http_foo_responses)
async def foo(request: HttpFooReq) -> MyORJSONResponse:
    result: FooResult = DomainService.foo(request.x)

    if result.x:
        return MyORJSONResponse(content=HttpFooResp(result=result.x))
    else:
        if result.error and result.error in DOMAIN_ERROR_TO_HTTP_ERROR_MAP:
            return get_error(http_foo_responses, 422, DOMAIN_ERROR_TO_HTTP_ERROR_MAP[result.error])
        else:
            logger.warning('unknown service error in handler')
            return get_error(http_foo_responses, 500, UnknownError.ErrorCode.UNKNOWN)


@click.group()
def cli() -> None:
    pass


@cli.command('run_server')
def run_server() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


@cli.command('openapi_docs')
def openapi_docs() -> None:
    yaml_str = StringIO()
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.dump(app.openapi(), yaml_str)
    click.echo(yaml_str.getvalue(), nl=False)


if __name__ == '__main__':
    cli()
