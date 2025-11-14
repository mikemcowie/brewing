"""HTTP Health check endpoints implementation."""

from dataclasses import dataclass
from brewing.http import ViewSet, ViewsetOptions, self, status
from brewing.app import BrewingOptions
from fastapi.responses import PlainTextResponse, Response
from typing import Protocol
from pydantic import BaseModel, Field
import structlog


logger = structlog.get_logger()


class HealthCheckResult(BaseModel):
    """Data structure for health check results."""

    passed: bool = Field(
        default=..., title="Passed", description="Whether the given check passed."
    )
    dependencies: dict[str, bool] = Field(
        default=..., title="dependency check results."
    )


class HealthCheckDependency(Protocol):
    """Protocol for health check dependenies."""

    async def is_alive(self, timeout: float) -> bool:
        """Return whether the dependency is alive."""
        ...


@dataclass(kw_only=True)
class HealthCheckOptions(ViewsetOptions):
    """Options for the healthcheck viewset."""

    timeout: float = 1.0

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

    async def _check(self, dependency: HealthCheckDependency):
        try:
            await dependency.is_alive(self.viewset_options.timeout)
            return True
        except Exception:
            logger.exception("dependency failure", dependency=dependency)
            return False

    @livez.GET(response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
    async def is_alive(self):
        """Return whether the application is responsive."""
        return "alive"

    @readyz.GET(
        response_model=HealthCheckResult,
        status_code=status.HTTP_200_OK,
        responses={
            503: {"model": HealthCheckResult, "description": "Health check failed."}
        },
    )
    async def is_ready(self, response: Response):
        """Return whether the application is ready to receive traffic."""
        dependencies = {"database": await self._check(self.viewset_options.database)}
        passed = all(dependencies.values())
        response.status_code = (
            status.HTTP_200_OK if passed else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return HealthCheckResult(passed=passed, dependencies=dependencies)
