from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Agent:
    """A Person or Organization."""

    name: str = None
    email: str = None

    def is_valid(self) -> bool:
        return bool(self.name)


@dataclass(slots=True)
class Person(Agent):
    pass


@dataclass(slots=True)
class Organization(Agent):
    url: str = None
