import json
from typing import ClassVar

from brewing import CLI


class PublishMatrix(CLI):
    PACKAGES: ClassVar[dict[str, str]] = {
        "brewing": "framework",
        "brewinglib-cli": "libs/cli",
    }

    def matrix(self, event_name: str):
        is_test_pypi = event_name == "push"
        environment = "testpypi" if is_test_pypi else "pypi"
        base_url = "testpypi.org" if is_test_pypi else "pypi.org"
        matrix = {
            "include": [
                {
                    "name": package,
                    "path": package_path,
                    "environment_name": environment,
                    "environment_url": f"https://{base_url}/p/{package}",
                    "repository_url": f"https://{base_url}/legacy",
                }
                for package, package_path in self.PACKAGES.items()
            ]
        }
        print(json.dumps(matrix))  # noqa: T201


if __name__ == "__main__":
    PublishMatrix("publish-matrix")()
