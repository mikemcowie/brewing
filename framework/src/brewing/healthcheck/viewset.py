from brewing.http import ViewSet, self, status
from fastapi.responses import PlainTextResponse


class HealthCheckViewset(ViewSet):
    livez = self("livez")
    readyz = self("readyz")

    @livez.GET(response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
    def is_alive(self):
        return "alive"

    @readyz.GET(response_class=PlainTextResponse, status_code=status.HTTP_200_OK)
    def is_ready(self):
        return "ready"
