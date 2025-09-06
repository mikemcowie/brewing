from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable

    import typer

    from cauldron_incubator.db.database import Migrations
    from cauldron_incubator.http import CauldronHTTP


class CLIProviderType(Protocol):
    def __call__(
        self,
        api_factory: Callable[[], CauldronHTTP],
        dev_api_factory: Callable[[], CauldronHTTP],
        migrations: Migrations[Any],
    ) -> typer.Typer: ...


class BaseConfiguration:
    """Basic configuration holder for an application.

    Cannot be instantiated directly; must be subclassed to
    provide all the required class attributes
    """

    description: str
    title: str
    version: str
    cli_provider: CLIProviderType

    def __new__(cls):
        if unimplemented_annotations := set(get_type_hints(cls).keys()).difference(
            cls.__dict__.keys()
        ):
            raise TypeError(
                f"required class attributes missing: {sorted(set(unimplemented_annotations))}. "
                "Create a subclass that implements these as class attributes."
            )
        return super().__new__(cls)
