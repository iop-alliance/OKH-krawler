# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from typing import Any

import toml

from krawl.errors import SerializerError
from krawl.fetcher.result import FetchResult
from krawl.model.project import Project
from krawl.serializer import Serializer
from krawl.serializer.json_serializer import JsonSerializer

# def _clean_dict_entry(pair: tuple[str, Any]) -> bool:
#     key, value = pair
#     if value >= 8.5:
#         return True  # keep pair in the filtered dictionary
#     else:
#         return False  # filter pair out of the dictionary

# def _clean_dict_recursive(content: dict[str, Any]) -> dict[str, Any]:
#     dict_clean: dict[str, Any] = dict(filter(_clean_dict_entry, content.items()))

#     return dict_clean


# From <https://stackoverflow.com/a/68323369/586229>
def dictionary_stripper(data: dict | None) -> dict | None:
    new_data = {}

    # Only iterate if the given dict is not None
    if data:
        for k, v in data.items():
            if isinstance(v, dict):
                v = dictionary_stripper(v)
            elif isinstance(v, list):
                v = list_stripper(v)

            # ideally it should be not in, second you can also add a empty list if required
            if v not in ("", None, {}, []):
                new_data[k] = v

        # Only if you want the root dict to be None if empty
        if not new_data:  # this is equivalent to `new_data == {}`
            return None
        return new_data
    return None


def list_stripper(data: list | None) -> list | None:
    new_data = []

    # Only iterate if the given dict is not None
    if data:
        for v in data:
            if isinstance(v, dict):
                v = dictionary_stripper(v)
            elif isinstance(v, list):
                v = list_stripper(v)

            # ideally it should be not in, second you can also add a empty list if required
            if v not in ("", None, {}, []):
                new_data.append(v)

        # Only if you want the root dict to be None if empty
        if not new_data:  # this is equivalent to `new_data == []`
            return None
        return new_data
    return None


class TOMLSerializer(Serializer):

    @classmethod
    def extensions(cls) -> list[str]:
        return ["toml"]

    def __init__(self) -> None:
        self.json_serializer = JsonSerializer()

    def serialize(self, fetch_result: FetchResult, project: Project) -> str:
        try:
            # serialized = toml.dumps(project.as_dict())
            project_json_serialized: str = self.json_serializer.serialize(fetch_result, project)
            project_dict: dict = json.loads(project_json_serialized)
            project_dict_clean = dictionary_stripper(project_dict)
            if not project_dict_clean:
                raise SerializerError(
                    f"No data left after removing empty parts; regarding project '{fetch_result.data_set.hosting_unit_id}'"
                )
            serialized = toml.dumps(project_dict_clean)
        except Exception as err:
            raise SerializerError(
                f"Failed to serialize TOML for project '{fetch_result.data_set.hosting_unit_id}': {err}") from err
        return serialized
