"""Contextvars for active run / span."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

from agentelemetry.schemas import RunEvent, SpanEvent

_current_client: ContextVar[object | None] = ContextVar("agentelemetry_client", default=None)
_current_run: ContextVar[RunEvent | None] = ContextVar("agentelemetry_run", default=None)
_current_span: ContextVar[SpanEvent | None] = ContextVar("agentelemetry_span", default=None)


@dataclass
class ActiveContext:
    run: RunEvent | None = None
    span: SpanEvent | None = None


def set_client(client: object | None) -> None:
    _current_client.set(client)


def get_client() -> object | None:
    return _current_client.get()


def set_run(run: RunEvent | None) -> None:
    _current_run.set(run)


def get_run() -> RunEvent | None:
    return _current_run.get()


def set_span(span: SpanEvent | None) -> None:
    _current_span.set(span)


def get_span() -> SpanEvent | None:
    return _current_span.get()


def get_active() -> ActiveContext:
    return ActiveContext(run=get_run(), span=get_span())
