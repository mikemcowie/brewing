from brewinglib.db import testing


def test_env_adds_variable_and_cleans_it_up():
    environ = {"value1": "wontchange", "value2": "will_be_changed"}
    new_env = {"value2": "changed_to_this", "value3": "was_added"}
    with testing.env(new_env=new_env, environ=environ):
        assert environ == {
            "value1": "wontchange",
            "value2": "changed_to_this",
            "value3": "was_added",
        }, "issue with patching"
    assert environ == {"value1": "wontchange", "value2": "will_be_changed"}, (
        "issue with cleanup"
    )
