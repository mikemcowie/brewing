import pytest

from project_manager.resources import models, repo


def test_cannot_instantiate_unspecialized_repo():
    with pytest.raises(NotImplementedError):
        repo.CrudRepository(object(), object())  # type: ignore
    repo.CrudRepository[models.Resource](object(), object())  # type: ignore
