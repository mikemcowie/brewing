from __future__ import annotations

import random
import string
from pathlib import Path
from tempfile import TemporaryDirectory

from brewing.http import ViewSet, root, status, testing
from brewing.http.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)


class TestBrewingResponse:
    class ResponseTypeTestViews(ViewSet):
        # Random bytes to test the streaming response with.
        random_bytes = random.randbytes(1024)
        random_string = "".join(random.choice(string.ascii_letters) for _ in range(100))

        @root("text").GET()
        async def text(self):
            return PlainTextResponse(content="foo")

        @root("json").GET()
        async def json(self):
            return JSONResponse(content={"foo": "bar"})

        @root("html").GET()
        async def html(self):
            return HTMLResponse(content="<html></html>")

        @root("redirect").GET()
        async def redirect(self):
            return RedirectResponse("/html")

        @root("stream").GET()
        def stream(self):
            def iterbytes():
                with TemporaryDirectory(delete=False) as temp:
                    source_file = Path(temp) / "file"
                    source_file.write_bytes(self.random_bytes)
                    with source_file.open("br") as f:
                        yield from f

            iterator = iterbytes()
            return StreamingResponse(iterator)

        @root("file").GET()
        def file(self):
            with TemporaryDirectory(delete=False) as temp:
                source_file = Path(temp) / "file"
                source_file.write_text(self.random_string)

            return FileResponse(source_file)

    def client(self):
        return testing.new_client(self.ResponseTypeTestViews())

    def test_plain(self):
        result = self.client().get("/text")
        assert result.status_code == status.HTTP_200_OK
        assert result.text == "foo"
        assert result.headers.get("content-type") == "text/plain; charset=utf-8"

    def test_json(self):
        result = self.client().get("/json")
        assert result.status_code == status.HTTP_200_OK
        assert result.json() == {"foo": "bar"}
        assert result.headers.get("content-type") == "application/json"

    def test_html(self):
        result = self.client().get("/html")
        assert result.status_code == status.HTTP_200_OK
        assert result.text == "<html></html>"
        assert result.headers.get("content-type") == "text/html; charset=utf-8"

    def test_redirect(self):
        result = self.client().get("/redirect", follow_redirects=False)
        assert result.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert result.headers.get("location") == "/html"
        result_following_redirect = self.client().get(
            "/redirect", follow_redirects=True
        )
        assert result_following_redirect.status_code == status.HTTP_200_OK
        assert result_following_redirect.text == "<html></html>"
        assert (
            result_following_redirect.headers.get("content-type")
            == "text/html; charset=utf-8"
        )

    def test_stream(self):
        with self.client().stream("GET", "/stream") as stream:
            result = stream.read()
        assert result == self.ResponseTypeTestViews.random_bytes

    def test_file(self):
        result = self.client().get("/file")
        assert result.status_code == status.HTTP_200_OK
        assert result.text == self.ResponseTypeTestViews.random_string
