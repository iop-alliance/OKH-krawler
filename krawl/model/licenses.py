# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2021 Alec Hanefeld <alec@konek.to>
# SPDX-FileCopyrightText: 2021 hoijui <hoijui.quaero@gmail.com>
# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from krawl.log import get_child_logger

_licenses: dict[str, License]
_name_to_id: dict[str, str]
log = get_child_logger("licenses")


class LicenseType(StrEnum):
    UNKNOWN = "unknown"
    WEAK = "weak"
    STRONG = "strong"
    PERMISSIVE = "permissive"
    PROPRIETARY = "proprietary"

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_string(cls, type_: str | None) -> LicenseType:
        type_ = type_ or "unknown"
        type_ = type_.lower()
        try:
            return cls(type_)
        except ValueError:
            return cls.UNKNOWN

    def is_open(self) -> bool:
        match self:
            case self.WEAK | self.STRONG | self.PERMISSIVE:
                return True
            case self.UNKNOWN | self.PROPRIETARY:
                return False
            case _:
                raise NotImplementedError


@dataclass(slots=True, frozen=True)
class License:  # pylint: disable=too-many-instance-attributes
    _id: str
    name: str
    reference_url: str
    type_: LicenseType = LicenseType.UNKNOWN
    details_url: str | None = None
    is_spdx: bool = False
    is_osi_approved: bool = False
    is_fsf_libre: bool = False
    is_blocked: bool = True

    def id(self) -> str:
        return self._id

    def __str__(self) -> str:
        return self.id()

    def __repr__(self) -> str:
        return self.id()


def _normalize_name(name: str) -> str:
    return str(unicodedata.normalize('NFKD', name).casefold().encode('ascii', 'ignore')).strip()


def _init_licenses() -> tuple[dict[str, License], dict[str, str]]:
    """Load the licenses and blocklist the included assets files.

    The lists originate from:
        spdx-licenses.json: https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json
        spdx-blocklist.json: https://raw.githubusercontent.com/OPEN-NEXT/LOSH-Licenses/main/SPDX-blocklist.json
    """
    assets_path: Path = Path(__file__).parent.parent / "assets"

    licenses_file = assets_path / "spdx-licenses.json"
    with licenses_file.open("r") as f:
        raw_license_info: dict[str, Any] = json.load(f)
        license_info: dict[str, dict[str, Any]] = {
            _normalize_name(lic["licenseId"]): lic for lic in raw_license_info["licenses"]
        }
    licenses_extra_file: Path = assets_path / "spdx-licenses-extra.json"
    with licenses_extra_file.open("r") as f:
        raw_license_extra_info: dict[str, Any] = json.load(f)
        license_extra_info: dict[str, dict[str, Any]] = {
            _normalize_name(lic["licenseId"]): lic for lic in raw_license_extra_info["licenses"]
        }
    for name in license_extra_info:
        if name in license_info:
            license_info[name] = _merge_dicts(license_info[name], license_extra_info[name])

    licenses: dict[str, License] = {
        n: License(
            _id=lic_inf["licenseId"],
            name=lic_inf["name"],
            type_=LicenseType.from_string(lic_inf.get("type")),
            reference_url=lic_inf["reference"],
            details_url=lic_inf["detailsUrl"],
            is_spdx=True,
            is_osi_approved=lic_inf["isOsiApproved"],
            is_fsf_libre=lic_inf.get("isFsfLibre", False),
            is_blocked=lic_inf.get("isBlocked", False),
        ) for n, lic_inf in license_info.items()
    }

    # create mapping between license name and id (performance wise)
    name_to_id: dict[str, str] = {_normalize_name(lic.name): key for key, lic in licenses.items()}

    return licenses, name_to_id


def _merge_dicts(x: Mapping[Any, Any], y: Mapping[Any, Any]) -> dict[Any, Any]:
    """Recursively merges two dicts.

    When keys exist in both the value of 'y' is used.

    Args:
        x (dict): First dict
        y (dict): Second dict

    Returns:
        dict: The merged dict
    """
    assert isinstance(x, Mapping) and isinstance(y, Mapping)

    merged = dict(x, **y)

    for key, x_val in x.items():
        if isinstance(x_val, Mapping) and key in y:
            merged[key] = _merge_dicts(x_val, y[key])
    return merged


def get_licenses() -> list:
    return list(_licenses.values())


def get_blocked():
    return filter(lambda lic: lic.is_blocked, _licenses.values())


def get_by_id(id: str) -> License | None:
    normalized = _normalize_name(id)
    if normalized in _licenses:
        return _licenses[normalized]
    return None


def get_by_id_or_name_required(id_or_name: str) -> License:
    if not id_or_name:
        raise ValueError("id_or_name is required")
    normalized = _normalize_name(id_or_name)
    if normalized in _licenses:
        return _licenses[normalized]
    if normalized in _name_to_id:
        return _licenses[_name_to_id[normalized]]
    log.warn(f'WARN: Non-SPDX license detected: "{id_or_name}"')

    return License(
        _id=f'LicenseRef-{id_or_name}',
        name=id_or_name,
        reference_url=f"file://LICENSES/LicenseRef-{id_or_name}.txt",
    )


def get_by_id_or_name(id_or_name: str | None) -> License | None:
    if id_or_name:
        try:
            return get_by_id_or_name_required(id_or_name)
        except ValueError:
            pass
    return None


def get_spdx_by_id_or_name(id_or_name: str) -> str | None:
    spdx_id = None
    license = get_by_id_or_name(id_or_name)
    if license:
        spdx_id = license.id()
    return spdx_id


# preload the license on import
_licenses, _name_to_id = _init_licenses()

__unknown_license__: License = License(
    _id="LicenseRef-NOASSERTION",
    name="No license statement is present; This equals legally to All Rights Reserved (== proprietary)",
    reference_url="https://en.wikipedia.org/wiki/All_rights_reserved",
    type_=LicenseType.UNKNOWN,
    is_spdx=False,
    is_osi_approved=False,
    is_fsf_libre=False,
    is_blocked=True,
)
__proprietary_license__: License = License(
    _id="LicenseRef-AllRightsReserved",
    name="All Rights Reserved (== proprietary)",
    reference_url="https://en.wikipedia.org/wiki/All_rights_reserved",
    type_=LicenseType.PROPRIETARY,
    is_spdx=False,
    is_osi_approved=False,
    is_fsf_libre=False,
    is_blocked=True,
)
