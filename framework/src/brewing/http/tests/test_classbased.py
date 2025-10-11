"""Class based viewset tests"""

from typing import Annotated
from http import HTTPMethod
from brewing.http import ViewSet, status, self
from brewing.http.path import TrailingSlashPolicy, DeferredDecoratorCall
from brewing.http.tests.helpers import SomeData, new_client
from fastapi import APIRouter, Depends, HTTPException


class ItemViewSet(ViewSet):
    def __init__(
        self,
        root_path: str = "",
        router: APIRouter | None = None,
        trailing_slash_policy: TrailingSlashPolicy = TrailingSlashPolicy.default(),
    ):
        super().__init__(root_path, router, trailing_slash_policy)
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
            id = 0
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
    assert ItemViewSet.list_items._deferred_decorations == [
        DeferredDecoratorCall(self, HTTPMethod.GET, args=(), kwargs={})
    ]
    assert ItemViewSet.create_item._deferred_decorations == [
        DeferredDecoratorCall(
            self, HTTPMethod.POST, args=(), kwargs={"status_code": 201}
        )
    ]
    assert ItemViewSet.get_item._deferred_decorations == [
        DeferredDecoratorCall(ItemViewSet.item_id, HTTPMethod.GET, args=(), kwargs={})
    ]
    assert ItemViewSet.update_item._deferred_decorations == [
        DeferredDecoratorCall(ItemViewSet.item_id, HTTPMethod.PUT, args=(), kwargs={})
    ]
    assert ItemViewSet.delete_item._deferred_decorations == [
        DeferredDecoratorCall(
            ItemViewSet.item_id, HTTPMethod.DELETE, args=(), kwargs={}
        )
    ]


def test_post_create_items():
    """Test the api root endponts - list and create."""
    client = new_client(ItemViewSet())
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
    client = new_client(ItemViewSet())
    initial_get = client.get("/1")
    assert initial_get.status_code == status.HTTP_404_NOT_FOUND

    data = SomeData(something=[1], data="bar")
    create_result = client.post("/", json=data.model_dump(mode="json"))
    assert create_result.status_code == status.HTTP_201_CREATED

    second_get = client.get("/1")
    assert second_get.status_code == status.HTTP_200_OK
    assert SomeData.model_validate(second_get.json()) == data


if __name__ == "__main__":
    import uvicorn
    from brewing.http import BrewingHTTP

    app = BrewingHTTP()
    app.include_viewset(ItemViewSet())
    uvicorn.run(app)
