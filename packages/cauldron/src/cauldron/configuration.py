from typing import Protocol, get_type_hints

import typer


class CLIProviderType(Protocol):
    def __call__(self, api_string_ref: str, dev_api_string_ref: str) -> typer.Typer: ...


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
                f"required class attributes missing: {sorted(set(unimplemented_annotations))}. Create a subclass that implements these as class attributes."
            )
        return super().__new__(cls)
