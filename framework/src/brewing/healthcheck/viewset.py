"""HTTP Health check endpoints implementation."""

from dataclasses import dataclass
from brewing.http import ViewSet, ViewsetOptions, self, status
from fastapi.responses import PlainTextResponse


@dataclass
class HealthCheckOptions(ViewsetOptions):
    """Options for the healthcheck viewset."""


class HealthCheckViewset(ViewSet[HealthCheckOptions]):
    """
    A viewset implementing basic health checks.

    This is intended for a loadbalancer or alerting system to query
    to determine whether the application is ready to receive traffic.
    """

    livez = self("livez")
    readyz = self("readyz")

    @livez.GET(response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
    def is_alive(self):
        """Return whether the application is responsive."""
        return "alive"

    @readyz.GET(response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
    def is_ready(self):
        """Return whether the application is ready to receive traffic."""
        return "ready"
