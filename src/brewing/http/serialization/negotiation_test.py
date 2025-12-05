from abc import ABC, abstractmethod
from typing import Any

import pytest

from brewing.http.serialization.base import Renderer
from brewing.http.serialization.negotiation import (
    ContentNegotiation,
    Negotiator,
    NotAcceptable,
    TrivialNegotiator,
)


class BaseTestNegotiation(ABC):
    @abstractmethod
    def get_negotiator(self) -> Negotiator:
        """Return the negotiator under test."""

    def renderer_caller(self):
        def _func(obj: object):
            return obj

        return _func

    def renderer_factory(self, content_type: str):
        type(
            "Renderer",
            (Renderer,),
            {"content_type": content_type, "__call__": self.renderer_caller},
        )

    def test_negotiation_fails_if_no_renderer(self):
        with pytest.raises(NotAcceptable):
            self.get_negotiator().select(accepts="", renderers=[])


class TestTrivialNegotiator(BaseTestNegotiation):
    def get_negotiator(self) -> Negotiator:
        return TrivialNegotiator()


class TestContentNegotiator(BaseTestNegotiation):
    def get_negotiator(self) -> Negotiator:
        return ContentNegotiation()

    class DummyRenderer(Renderer[Any, Any]):
        def __call__(self, obj: Any) -> Any:
            raise NotImplementedError()

    class PlainTextRenderer(DummyRenderer):
        content_type = "text/plain"

    class JSONRenderer(DummyRenderer):
        content_type = "application/json"

    class YAMLRenderer(DummyRenderer):
        content_type = "application/yaml"

    class HTMLRenderer(DummyRenderer):
        content_type = "text/html"

    plain_text_renderer = PlainTextRenderer()
    json_renderer = JSONRenderer()
    yaml_renderer = YAMLRenderer()
    html_renderer = HTMLRenderer()
    all_renderers = (plain_text_renderer, json_renderer, yaml_renderer, html_renderer)

    def test_none_acceptable(self):
        with pytest.raises(NotAcceptable):
            self.get_negotiator().select(
                accepts=["application/csv"], renderers=self.all_renderers
            )

    def test_any_acceptable(self):
        assert (
            self.get_negotiator().select(accepts=["*/*"], renderers=self.all_renderers)
            == self.plain_text_renderer
        )

    def test_fallback_any_acceptable(self):
        assert (
            self.get_negotiator().select(
                accepts=["application/csv", "*/*;q=0.9"], renderers=self.all_renderers
            )
            == self.plain_text_renderer
        )

    def test_preferred_optiom_returned(self):
        assert (
            self.get_negotiator().select(
                accepts=["application/yaml", "application/json;q=0.9"],
                renderers=self.all_renderers,
            )
            == self.yaml_renderer
        )

    def test_wildcard_subtype(self):
        assert (
            self.get_negotiator().select(
                accepts=["application/*", "text/html;q=0.9"],
                renderers=self.all_renderers,
            )
            == self.json_renderer
        )
