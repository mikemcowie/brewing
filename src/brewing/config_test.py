"""Configurations: the data holders used to configure brewing and its components."""

from __future__ import annotations

from brewing import config as c


class TargetOptions(c.BaseOptions):
    name: str


class Target(c.EnvPushable[TargetOptions]):
    pass


def test_type_serializer_transmitted_by_environment():
    """Affirm we can use environment variables to transmit the object"""
    target = Target(TargetOptions(name="something"))
    env_var = "SOME-VAR"
    with c.push_to_env(target, env_var):
        final = c.pull_from_env(env_var, Target)
    assert type(final) is type(target)
    assert final.options == target.options
    assert final.__dict__ == target.__dict__
