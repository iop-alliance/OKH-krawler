from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# from krawl.model.licenses import get_spdx_by_id_or_name as get_license
# from krawl.model.util import parse_date


@dataclass(slots=True, unsafe_hash=True)
class File:  # pylint: disable=too-many-instance-attributes
    """File data model."""

    name: str = None
    path: Path = None
    mime_type: str = None
    url: str = None
    frozen_url: str = None  # frozen URL is bound to a specific version of the file, e.g. a git commit
    created_at: datetime = None
    last_visited: datetime = None
    last_changed: datetime = None
    license: str = None
    licensor: str = None

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
