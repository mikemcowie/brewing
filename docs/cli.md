# CLI

!!! note

    The main goal of this package is to make it easier to build embedded command lines, so that for example
    you can provide a command line as part of a library, and make it easy for consumers to embed the command line
    into their own wider CLI application.

    If you just want a simple CLI in the global scope of a python module, this package offers nothing compared to typer.

Cauldron's CLI package is an object-oriented wrapper around Tiangolo's [Typer](https://typer.tiangolo.com/), which itself
builds on PalletsProjects' [click](https://click.palletsprojects.com/en/stable/).


To write a CLI, simply inherit from cauldron.cli.CLI, write a python class with type hints on the methods,
and instantiate an instance of that class. Cauldron CLI will automatically build a CLI based on the public methods of the class.



```python
from cauldron.cli import CLI


class MyCLI(CLI):

    def greet(self, message:str):
        print("message")


cli = MyCLI().typer
cli()

```


typer is transparently used to parse the methods, so all of its documentation about how to declare arguments and options is applicable.
To explicitely declare a parameter to be an option, use typing.Annotated with typer's Option class.


```python
from typing import Annotated
from typer import Option
from cauldron.cli import CLI


class MyCLI(CLI):

    def greet(self, message:[Annotated[str, Option()]]):
        print("message")

```
