# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

# from krawl.model.licenses import get_spdx_by_id_or_name as get_license
# from krawl.model.util import parse_date


@dataclass(slots=True, unsafe_hash=True)
class File:  # pylint: disable=too-many-instance-attributes
    """File data model."""
    name: str | None = None
    path: Path | None = None
    mime_type: str | None = None
    url: str | None = None
    frozen_url: str | None = None
    "frozen URL is bound to a specific version of the file, e.g. a git commit"
    created_at: datetime | None = None
    last_visited: datetime | None = None
    last_changed: datetime | None = None
    # NOTE We don;t want these here, as we want to promote file-level licensing information to be handled exclusively with REUSE/SPDX
    # license: str | None = None
    # licensor: str | None = None

    @property
    def extension(self):
        return self.path.suffix[1:].lower() if self.path else ""

    # @classmethod
    # def from_dict(cls, data: dict) -> File | None:
    #     if data is None:
    #         return None
    #     file = cls()
    #     file.name = data.get("name", None)
    #     file.path = Path(data["path"]) if data.get("path") is not None else None
    #     file.mime_type = data.get("mime-type", None)
    #     file.url = data.get("url", None)
    #     file.frozen_url = data.get("frozen-url", None)
    #     file.created_at = parse_date(data.get("created-at"))
    #     file.last_visited = parse_date(data.get("last-visited"))
    #     file.last_changed = parse_date(data.get("last-changed"))
    #     file.license = get_by_id_or_name(data.get("license", None))
    #     file.licensor = data.get("licensor", None)
    #     return file

    # def as_dict(self) -> dict:
    #     return {
    #         "name": self.name,
    #         "path": str(self.path),
    #         "mime-type": self.mime_type,
    #         "url": self.url,
    #         "frozen-url": self.frozen_url,
    #         "created-at": self.created_at.isoformat() if self.created_at is not None else None,
    #         "last-visited": self.last_visited.isoformat() if self.last_visited is not None else None,
    #         "last-changed": self.last_changed.isoformat() if self.last_changed is not None else None,
    #         "license": str(self.license),
    #         "licensor": self.licensor,
    #     }


class ImageSlot(StrEnum):
    """Any of a predefined (by OKH) set of values.
An image could fill multiple slots,
but each slot can be filled at most once within a design.
This is useful for things like the project-icon,
or the left-side view of the 3D model."""
    LOGO = "logo"
    ICON_MAIN = "icon-main"
    ICON_MAIN_BW = "icon-main-bw"
    """black&white"""
    SOCIAL = "social"
    """social media preview"""
    ORGANIZATION_LOGO = "organization-logo"
    ORGANIZATION_LOGO_BW = "organization-logo-bw"
    """too much?"""
    SYMBOL = "symbol"
    """An icon is a simple image that represents a real thing.
    For example, a shopping cart icon.

    A symbol is a simple image whose meaning must be learned.
    For example, most traffic signage is made of symbols.
    A "no parking" sing with a P crossed out with red
    needs to be learned to be understood.

    (source: [flaticon.com](https://www.flaticon.com/blog/difference-between-symbols-and-icons/))"""
    PHOTO_THING_MAIN = "photo-thing-main"
    PHOTO_PACKAGING = "photo-packaging"
    MODEL_FROM_LEFT = "model-from-left"
    MODEL_FROM_RIGHT = "model-from-right"
    MODEL_FROM_TOP = "model-from-top"
    MODEL_FROM_BOTTOM = "model-from-bottom"
    MODEL_FROM_FRONT = "model-from-front"
    MODEL_FROM_BACK = "model-from-back"
    MODEL_3D = "model-3d"
    MODEL_MAIN = "model-main"

    # TODO
    # echo "    photo
    # icon
    # logo
    # model
    # artistic
    # diagram
    # color
    # bnw
    # screenshot" | awk '{
    #     arr_size = split($0, all, "(")

    #     name = all[1]
    #     gsub("_", "-", name)
    #     gsub("[ \t]+", "", name)
    #     name_const = toupper(name)
    #     gsub("-", "_", name_const)
    #     name_str = name
    #     print(name_const " = \"" name_str "\"")
    #     if (arr_size > 1) {
    #         desc = all[2]
    #         gsub(")", "", desc)
    #         gsub("^[ \t]+", "", desc)
    #         gsub("[ \t]+$", "", desc)
    #         print("\"\"\"" desc "\"\"\"")
    #     }
    # }'
    # pass


class ImageTag(StrEnum):
    """A number of predefined+self-defined values.
An image could have 0 to many tags attached.
Each tag could be used by multiple images."""
    PHOTO = "photo"
    ICON = "icon"
    LOGO = "logo"
    MODEL = "model"
    ARTISTIC = "artistic"
    DIAGRAM = "diagram"
    COLOR = "color"
    BNW = "bnw"
    SCREENSHOT = "screenshot"


@dataclass(slots=True, unsafe_hash=True)
class Image(File):  # pylint: disable=too-many-instance-attributes
    """File data model."""
    slots: set[ImageSlot] = field(default_factory=set)
    tags: set[ImageTag] = field(default_factory=set)
    # path: Path | None = None
    # mime_type: str | None = None
    # url: str | None = None
    # frozen_url: str | None = None
    # "frozen URL is bound to a specific version of the file, e.g. a git commit"
    # created_at: datetime | None = None
    # last_visited: datetime | None = None
    # last_changed: datetime | None = None
    # NOTE We don't want these here, as we want to promote file-level licensing information to be handled exclusively with REUSE/SPDX
    # license: str | None = None
    # licensor: str | None = None

    @classmethod
    def from_file(cls, file: File) -> Image:
        image = cls(
            name=file.name,
            path=file.path,
            mime_type=file.mime_type,
            url=file.url,
            frozen_url=file.frozen_url,
            created_at=file.created_at,
            last_visited=file.last_visited,
            last_changed=file.last_changed,
            # license=file.license,
            # licensor=file.licensor
        )
        return image
