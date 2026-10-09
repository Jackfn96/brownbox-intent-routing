from collections.abc import Callable

import pytest

from brownbox.classify import Step

# One (intent, guards) pair per customer message, from C1.
StepSpec = tuple[str, tuple[str, ...]]
MakeSteps = Callable[..., list[Step]]


@pytest.fixture
def make_steps() -> MakeSteps:
    """Build the router's steps through a conversation, one spec per customer message."""

    def build(*specs: StepSpec) -> list[Step]:
        return [Step(message=k, intent=i, guards=g) for k, (i, g) in enumerate(specs, start=1)]

    return build
