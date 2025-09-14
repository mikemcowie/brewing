import pytest
from brewinglib.db import testing, types


@pytest.mark.parametrize("db_type", types.DatabaseType)
def test_a_testing_implementation_defined_for_every_database_type(
    db_type: types.DatabaseType,
):
    testing_class = testing.TestingDatabase.implementations[db_type]
    assert issubclass(testing_class, testing.TestingDatabase)
    assert testing_class.db_type == db_type


def test_cannot_register_another_test_implementation_for_same_db_type():
    with pytest.raises(RuntimeError) as error:

        class DifferentSQLLiteTestDatabase(
            testing.TestingDatabase, db_type=types.DatabaseType.sqlite
        ):  # type: ignore
            pass

    expected_message = (
        "Cannot register test database class for db_type=<DatabaseType.sqlite: 'sqlite'>; "
        "implementation=<class 'brewinglib.db.testing.TestingSQLite'> is already registered"
    )

    assert expected_message in error.exconly()
    assert (
        testing.TestingDatabase.implementations[types.DatabaseType.sqlite]
        is testing.TestingSQLite
    )
