from __future__ import annotations

from enum import StrEnum


class Ref(StrEnum):
    """An object annotated with one of this enums variants,
    refers to the same property
    under the indicated  of the project.

    For example, if `my_data_set.license = Ref.DOCUMENTATION`,
    it means that this data-sts license is the same
    as the projects documentation license."""
    DOCUMENTATION = "Documentation"
