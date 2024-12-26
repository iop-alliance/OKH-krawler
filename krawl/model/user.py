from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class User:  # TODO Unused, can be removed
    """User data model."""

    name: str = None
    email: str = None
    username: str = None
    language: str = None
