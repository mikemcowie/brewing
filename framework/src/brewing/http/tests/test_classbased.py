"""Class based viewset tests"""

from typing import Annotated
from http import HTTPMethod
from brewing.http import ViewSet, ViewsetOptions, status, self
from brewing.http.path import DeferredDecoratorCall
from brewing.http.testing import new_client
from brewing.http.tests.helpers import SomeData
from fastapi import APIRouter, Depends, HTTPException


class ItemViewSet(ViewSet[ViewsetOptions]):
    def __init__(
        self,
        options: ViewsetOptions,
        router: APIRouter | None = None,
    ):
        super().__init__(options, router)
        # We make a rudimentary database being a simple dict
        self._db: dict[int, SomeData] = {}
        # And 2 more databases to track what has been deleted and replaced.
        self._deleted: dict[int, list[SomeData]] = {}
        self._replaced: dict[int, list[SomeData]] = {}

    @self.GET()
    def list_items(self) -> list[SomeData]:
        """List all the items."""
        return list(self._db.values())

    @self.POST(status_code=status.HTTP_201_CREATED)
    def create_item(self, item: SomeData) -> SomeData:
        """Create an item."""
        try:
            id = sorted(self._db.keys())[-1] + 1  # Find next key
        except IndexError:  # When nothing in the db, the above raised IndexError
            id = 1
        self._db[id] = item
        print(sorted(self._db.keys()))
        return item

    item_id = self("{item_id}")

    @item_id.DEPENDS()
    def item(self, item_id: int) -> SomeData:
        try:
            return self._db[item_id]
        except KeyError as error:
            raise HTTPException(
                detail=f"no item found with {item_id=}",
                status_code=status.HTTP_404_NOT_FOUND,
            ) from error

    @item_id.GET()
    def get_item(self, item: Annotated[SomeData, Depends(item)]):
        return item

    @item_id.PUT()
    def update_item(
        self,
        item_id: int,
        current_item: Annotated[SomeData, Depends(item)],
        item: SomeData,
    ):
        if not self._replaced.get(item_id):
            self._replaced[item_id] = []
        self._replaced[item_id].append(current_item)
        self._db[item_id] = item
        return item

    @item_id.DELETE()
    def delete_item(self, item_id: int, item: Annotated[SomeData, Depends(item)]):
        if not self._deleted.get(item_id):
            self._deleted[item_id] = []
        self._deleted[item_id].append(item)
        del self._db[item_id]


def test_deferred_annotations():
    assert ItemViewSet.item_id.path == "/{item_id}"
    assert ItemViewSet.list_items._deferred_decorations == [  # type: ignore[reportFunctionMemberAccess]
        DeferredDecoratorCall(self, HTTPMethod.GET, args=(), kwargs={})
    ]
    assert ItemViewSet.create_item._deferred_decorations == [  # type: ignore[reportFunctionMemberAccess]
        DeferredDecoratorCall(
            self, HTTPMethod.POST, args=(), kwargs={"status_code": 201}
        )
    ]
    assert ItemViewSet.get_item._deferred_decorations == [  # type: ignore[reportFunctionMemberAccess]
        DeferredDecoratorCall(ItemViewSet.item_id, HTTPMethod.GET, args=(), kwargs={})
    ]
    assert ItemViewSet.update_item._deferred_decorations == [  # type: ignore[reportFunctionMemberAccess]
        DeferredDecoratorCall(ItemViewSet.item_id, HTTPMethod.PUT, args=(), kwargs={})
    ]
    assert ItemViewSet.delete_item._deferred_decorations == [  # type: ignore[reportFunctionMemberAccess]
        DeferredDecoratorCall(
            ItemViewSet.item_id, HTTPMethod.DELETE, args=(), kwargs={}
        )
    ]


def test_post_create_items():
    """Test the api root endponts - list and create."""
    client = new_client(ItemViewSet(ViewsetOptions()))
    list_result = client.get("/")
    assert list_result.status_code == status.HTTP_200_OK, list_result.json()
    assert list_result.json() == []
    data = SomeData(something=[1], data="bar")
    create_result = client.post("/", json=data.model_dump(mode="json"))
    assert create_result.status_code == status.HTTP_201_CREATED
    assert SomeData.model_validate(create_result.json()) == data
    list_result2 = client.get("/")
    assert len(list_result2.json()) == 1


def test_get_update_delete():
    """Test the endpoints that involve the instance_id and hence the dependency"""
    client = new_client(ItemViewSet(ViewsetOptions()))
    initial_get = client.get("/1")
    assert initial_get.status_code == status.HTTP_404_NOT_FOUND

    data = SomeData(something=[1], data="bar")
    create_result = client.post("/", json=data.model_dump(mode="json"))
    assert create_result.status_code == status.HTTP_201_CREATED

    second_get = client.get("/1")
    assert second_get.status_code == status.HTTP_200_OK
    assert SomeData.model_validate(second_get.json()) == data


def test_self_refers_to_correct_viewset():
    """Re-using a method via subclassing (or some other reference to another class) can cause in-place modifications.

    Make sure that "self" parameter of methods behaves as would be expected, as it seems that getting this wrong *could*
    lead to the dependency on the wrong viewset.
    """

    class VS1(ViewSet[ViewsetOptions]):
        value = "v1"

        @self.GET()
        def read_value(self):
            return self.value

    class VS2(VS1):
        value = "v2"

    assert new_client(VS1(ViewsetOptions())).get("/").text == '"v1"'
    assert new_client(VS2(ViewsetOptions())).get("/").text == '"v2"'


def test_fastapi_style_dependencies():
    """Test in-class fastapi-style dependency handling

    This needs our own logic, because we (may) conceptually need
    to rewrite the annotation to work with the instantiated class instance.
    """

    class VS(ViewSet[ViewsetOptions()]):
        def dep1(self):
            return "dep1"

        def dep2(self, dep1: Annotated[str, Depends(dep1)]):
            return dep1 + "dep2"

        def dep3(self, dep2: Annotated[str, Depends(dep2)]):
            return dep2 + "dep3"

        @self.GET()
        def read_value(self, dep3: Annotated[str, Depends(dep3)]):
            return dep3

    assert new_client(VS(ViewsetOptions())).get("/").text == '"dep1dep2dep3"'


if __name__ == "__main__":  # pragma: no cover
    # Can run this file as a script to debug.
    import uvicorn
    from brewing.http import BrewingHTTP

    app = BrewingHTTP()
    app.include_viewset(ItemViewSet(ViewsetOptions()))
    uvicorn.run(app)
