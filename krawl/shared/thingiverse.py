# SPDX-FileCopyrightText: 2022 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from csv import DictReader
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TypeAlias, TypedDict

from krawl.log import get_child_logger

log = get_child_logger("thingiverse")

# Maps Thingiverse license names to (search_id, SPDX-Id).
# If SPDX-Id is None, the license is not Open Source.
LICENSE_MAPPING = {
    "Creative Commons - Attribution": ("cc", "CC-BY-4.0"),
    "Creative Commons - Attribution - Share Alike": ("cc-sa", "CC-BY-SA-4.0"),
    "Creative Commons - Attribution - No Derivatives": ("cc-nd", None),
    "Creative Commons - Attribution - Non-Commercial": ("cc-nc", None),
    "Creative Commons - Attribution - Non-Commercial - Share Alike": ("cc-nc-sa", None),
    "Creative Commons - Attribution - Non-Commercial - No Derivatives": ("cc-nc-nd", None),
    "Creative Commons - Share Alike": ("cc-sa", "CC-BY-SA-4.0"),
    "Creative Commons - No Derivatives": ("cc-nd", None),
    "Creative Commons - Non-Commercial": ("cc-nc", None),
    "Creative Commons - Non Commercial - Share alike": ("cc-nc-sa", None),
    "Creative Commons - Non Commercial - No Derivatives": ("cc-nc-nd", None),
    "Creative Commons - Public Domain Dedication": ("pd0", "CC0-1.0"),
    "Public Domain": ("public", "CC0-1.0"),
    "GNU - GPL": ("gpl", "GPL-3.0-or-later"),
    "GNU - LGPL": ("lgpl", "LGPL-3.0-or-later"),
    "BSD": ("bsd", "BSD-4-Clause"),
    "BSD License": ("bsd", "BSD-4-Clause"),
    "Nokia": ("nokia", None),
    "All Rights Reserved": ("none", None),
    "Other": (None, None),
    "None": (None, None),
}
BROKEN_IMAGE_URL = 'https://cdn.thingiverse.com/'
RETRY_CODES = [429, 500, 502, 503, 504]
# BATCH_SIZE = 30
BATCH_SIZE = 1

t_url: TypeAlias = str
t_string: TypeAlias = str
# t_datetime: TypeAlias = str
t_datetime: TypeAlias = datetime


class ThingSearch(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - thing search."""
    total: int
    hits: list[Hit]


class Person(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - person."""
    id: int
    name: t_string
    first_name: t_string
    last_name: t_string
    url: t_url
    public_url: t_url
    thumbnail: t_url
    count_of_followers: int
    count_of_following: int
    count_of_designs: int
    make_count: int
    accepts_tips: bool
    is_following: bool
    location: t_string
    cover: t_url
    is_admin: bool
    is_moderator: bool
    is_featured: bool
    is_verified: bool


class ImageSize(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - image size."""
    type: t_string
    size: t_string
    url: t_url


class ThingImage(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - image."""
    id: int
    url: t_url
    name: t_string
    sizes: list[ImageSize]
    added: t_datetime


class Tag(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - tag."""
    name: t_string
    url: t_url
    count: int
    things_url: t_url
    absolute_url: t_string


class ZipFile(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - zip file."""
    name: t_string
    url: t_url


class ZipData(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - zip data."""
    files: list[ZipFile]
    images: list[ZipFile]


class Hit(TypedDict):
    """This maps precisely to the Thingiverse API response of a thing - hit."""
    id: int
    name: t_string
    thumbnail: t_url
    url: t_url
    public_url: t_url
    creator: Person | None
    added: t_datetime
    modified: t_datetime
    is_published: int
    is_wip: int
    is_featured: bool
    is_nsfw: bool
    is_ai: bool
    like_count: int
    is_liked: bool
    collect_count: int
    is_collected: bool
    comment_count: int
    is_watched: bool
    default_image: ThingImage
    description: t_string
    instructions: t_string | None
    description_html: t_string
    instructions_html: t_string
    details: t_string
    details_parts: list[dict]
    edu_details: t_string | None
    edu_details_parts: list[dict]
    license: t_string
    allows_derivatives: bool
    files_url: t_url
    images_url: t_url
    likes_url: t_url
    ancestors_url: t_url
    derivatives_url: t_url
    tags_url: t_string
    tags: list[Tag]
    categories_url: t_url
    file_count: int
    is_purchased: int
    app_id: int | None
    download_count: int
    view_count: int
    education: dict
    remix_count: int
    make_count: int
    app_count: int
    root_comment_count: int
    moderation: t_string | None
    is_derivative: bool
    ancestors: list
    can_comment: bool
    type_name: t_string
    is_banned: bool
    is_comments_disabled: bool
    needs_moderation: int
    is_decoy: int
    zip_data: ZipData


class ThingFile(TypedDict):
    """This maps precisely to the Thingiverse API response of a file - file."""
    id: int
    name: t_string
    size: int
    url: t_url
    public_url: t_url
    download_url: t_url
    threejs_url: t_url
    thumbnail: t_url
    default_image: ThingImage
    date: t_datetime
    formatted_size: t_string
    download_count: int
    direct_url: t_url


class StorageThingIdState(Enum):
    """The basic state of a thing ID on the platform."""
    DELETED = 1
    PROPRIETARY = 2
    OPEN_SOURCE = 3


class StorageThingMeta(TypedDict):
    """What we store for every thing ID."""
    id: int
    state: StorageThingIdState
    first_scrape: t_datetime | None
    last_scrape: t_datetime | None
    last_successful_scrape: t_datetime | None
    last_change: t_datetime | None
    attempted_scrapes: int
    scraped_changes: int


def read_all_os_thing_metas() -> list[tuple[StorageThingMeta, Path]]:
    metas_with_path: list[tuple[StorageThingMeta, Path]] = []
    tv_store_base: Path = Path("rust/workdir/thingiverse_store")
    for os_metas_slice_csv_file in tv_store_base.glob("data/*/open_source.csv"):
        slice_os_metas: list[StorageThingMeta] = read_thing_metas(os_metas_slice_csv_file)
        things_dir = os_metas_slice_csv_file.parent / "things"
        for meta in slice_os_metas:
            path = things_dir / f"{meta['id']}.json"
            metas_with_path.append((meta, path))
    return metas_with_path


def read_thing_metas_with_path(os_metas_slice_csv_file: Path) -> list[tuple[StorageThingMeta, Path]]:
    metas_with_path: list[tuple[StorageThingMeta, Path]] = []
    slice_os_metas: list[StorageThingMeta] = read_thing_metas(os_metas_slice_csv_file)
    things_dir = os_metas_slice_csv_file.parent / "things"
    for meta in slice_os_metas:
        path = things_dir / f"{meta['id']}.json"
        metas_with_path.append((meta, path))
    return metas_with_path


def read_thing_metas(thing_metas_csv_file: Path) -> list[StorageThingMeta]:
    metas: list[StorageThingMeta] = []
    # path = assets_path / (name + ".csv")
    with thing_metas_csv_file.open("r") as file_handle:
        csv_reader = DictReader(file_handle)
        for record in csv_reader:
            thing_meta_untyped: dict = record
            thing_meta: StorageThingMeta = thing_meta_untyped
            metas.append(thing_meta)
    return metas
