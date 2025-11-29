"""HTTP Health check endpoints implementation."""

from typing import Protocol

import structlog
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from brewing import current_database
from brewing.http import ViewSet, base_path, status

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


class HealthCheckViewset(ViewSet):
    """
    A viewset implementing basic health checks.

    This is intended for a loadbalancer or alerting system to query
    to determine whether the application is ready to receive traffic.
    """

    timeout: float = 1.0
    livez = base_path("livez")
    readyz = base_path("readyz")

    async def _check(self, dependency: HealthCheckDependency):
        try:
            await dependency.is_alive(self.timeout)
        except Exception:
            logger.exception("dependency failure", dependency=dependency)
            return False
        else:
            return True

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
        dependencies = {"database": await self._check(current_database())}
        passed = all(dependencies.values())
        response.status_code = (
            status.HTTP_200_OK if passed else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return HealthCheckResult(passed=passed, dependencies=dependencies)
