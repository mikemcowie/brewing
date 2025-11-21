import pytest
from sqlalchemy.orm import Mapped, mapped_column

from brewing.db import base


def test_subclass_of_base_is_abstract_with_own_metadata():
    class _MyBase(base.Base):
        pass

    class _MyModel(_MyBase):
        id: Mapped[int] = mapped_column(primary_key=True)

    assert _MyBase.__abstract__  # type: ignore
    with pytest.raises(AttributeError):
        _ = _MyBase.__table__
    assert _MyModel.__tablename__ == "_my_model"
    assert base.Base.metadata is not _MyBase.metadata
    assert _MyBase.metadata is _MyModel.metadata
