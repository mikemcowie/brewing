# brewing

[![CI](https://github.com/mikemcowie/brewing/actions/workflows/ci.yaml/badge.svg)](https://github.com/mikemcowie/brewing/actions/workflows/ci.yaml)

Brewing is a python application framework designed to solve problems well, and then get out of your way.



## Installation

Use your preferred python package manager to install brewing. The author strongly recommends [uv](https://docs.astral.sh/uv/).

```
uv add brewing
```

# Influences

Brewing attempts to take principals from various battle-tested frameworks.

## Rails

1.The [rails doctrine](https://rubyonrails.org/doctrine), especially:
   * *convention over configuration*
   * *the menu is omakase*
   * *provide sharp knives*

## Django

* The [*batteries included* ](https://docs.python.org/3/tutorial/stdlib.html#tut-batteries-included) principal
* Basically, following much of the rails doctrine in a python context.
* Class based views with close integration to the model/data layer.

## FastAPI

* Using type hints at runtime to setup HTTP endpoints.
* Brewing's ASGI application is a subclass of fastapi.FastAPI, and its key decorators are largely maintained.
