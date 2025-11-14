"""HTTP Health check endpoints implementation."""

from dataclasses import dataclass
from brewing.http import ViewSet, ViewsetOptions, self, status
from brewing.app import BrewingOptions
from fastapi.responses import PlainTextResponse, JSONResponse


@dataclass(kw_only=True)
class HealthCheckOptions(ViewsetOptions):
    """Options for the healthcheck viewset."""

    def __post_init__(self):
        self.database = BrewingOptions.current().database


class HealthCheckViewset(ViewSet[HealthCheckOptions]):
    """
    A viewset implementing basic health checks.

    This is intended for a loadbalancer or alerting system to query
    to determine whether the application is ready to receive traffic.
    """

    livez = self("livez")
    readyz = self("readyz")

    @livez.GET(response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
    async def is_alive(self):
        """Return whether the application is responsive."""
        return "alive"

    @readyz.GET(response_class=JSONResponse, status_code=status.HTTP_200_OK)
    async def is_ready(self):
        """Return whether the application is ready to receive traffic."""
        return {"database": await self.viewset_options.database.is_alive(timeout=1.0)}
