from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import validators

_sha1_pattern = re.compile(r"^[A-Fa-f0-9]{40}$")


class PlatformURL:

    def __init__(
        self,
        platform: str = None,
        owner: str = None,
        repo: str = None,
        path: str = None,
        branch: str = None,
    ) -> None:
        self.platform = platform
        self.owner = owner
        self.repo = repo
        self.path = path
        self.branch = branch

    @classmethod
    def from_url(cls, url: str) -> PlatformURL:
        if not (isinstance(url, str) and validators.url(url)):
            raise ValueError(f"invalid URL '{url}'")
        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        path_parts = Path(parsed_url.path).relative_to("/").parts
        platform_url = cls()

        if domain in ["github.com", "raw.githubusercontent.com"]:
            platform_url.platform = "github.com"
            platform_url.owner = path_parts[0] if len(path_parts) >= 1 else None
            platform_url.repo = path_parts[1] if len(path_parts) >= 2 else None
            if domain == "github.com":
                if len(path_parts) >= 4 and path_parts[2] in ["tree", "blob"]:
                    platform_url.branch = path_parts[3]
                    if len(path_parts) > 4:
                        platform_url.path = "/".join(path_parts[4:])
                elif len(path_parts) > 4 and path_parts[2] == "releases" and path_parts[3] == "tag":
                    platform_url.branch = path_parts[4]
                elif len(path_parts) > 3 and path_parts[2] == "commit":
                    platform_url.branch = path_parts[3]
            elif domain == "raw.githubusercontent.com":
                platform_url.branch = path_parts[2] if len(path_parts) >= 3 else None
                platform_url.path = "/".join(path_parts[3:]) if len(path_parts) >= 4 else None

        elif domain == "gitlab.com":
            platform_url.platform = "gitlab.com"
            platform_url.owner = path_parts[0] if len(path_parts) >= 1 else None
            platform_url.repo = path_parts[1] if len(path_parts) >= 2 else None
            if len(path_parts) >= 5 and path_parts[2] == "-" and path_parts[3] in ["tree", "blob", "raw"]:
                platform_url.branch = path_parts[4]
                if len(path_parts) > 5:
                    platform_url.path = "/".join(path_parts[5:])
            elif len(path_parts) >= 5 and path_parts[2] == "-" and path_parts[3] in ["commit", "tags"]:
                platform_url.branch = path_parts[4]

        elif domain == "wikifactory.com":
            platform_url.platform = "wikifactory.com"
            platform_url.owner = path_parts[0] if len(path_parts) >= 1 else None
            platform_url.repo = path_parts[1] if len(path_parts) >= 2 else None
            if len(path_parts) >= 4 and path_parts[2] in ["file", "files"]:
                platform_url.path = "/".join(path_parts[3:])
            elif len(path_parts) >= 4 and path_parts[2] == "v":
                platform_url.branch = path_parts[3]
                if len(path_parts) >= 6 and path_parts[4] in ["file", "files"]:
                    platform_url.path = "/".join(path_parts[5:])
        elif domain == "certification.oshwa.org":
            platform_url.platform = "oshwa.org"
            platform_url.repo = f"https://certification.oshwa.org/{path_parts[0]}"
            platform_url.path = path_parts[0]
        else:
            raise ValueError(f"unknown platfrom URL '{url}'")

        return platform_url

    def as_download_url(self) -> str:
        if not self.platform or not self.owner or not self.repo:
            raise ValueError("missing owner or repo")

        # format: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
        if self.platform == "github.com":
            if not self.branch:
                raise ValueError("missing branch")
            if self.path:
                path = f"/{self.owner}/{self.repo}/{self.branch}/{str(self.path)}"
            else:
                path = f"/{self.owner}/{self.repo}/{self.branch}"
            return str(urlunparse((
                "https",
                "raw.githubusercontent.com",
                path,
                None,
                None,
                None,
            )))

        # format: https://gitlab.com/{owner}/{repo}/-/raw/{branch}/{path}
        elif self.platform == "gitlab.com":
            if not self.branch:
                raise ValueError("missing branch")
            if self.path:
                path = f"/{self.owner}/{self.repo}/-/raw/{self.branch}/{str(self.path)}"
            else:
                path = f"/{self.owner}/{self.repo}/-/raw/{self.branch}"
            return str(urlunparse((
                "https",
                "gitlab.com",
                path,
                None,
                None,
                None,
            )))

        # format: https://projects.fablabs.io/{owner}/{repo}/contributions/{branch}/file/{path}
        elif self.platform == "wikifactory.com":
            if isinstance(self.branch, str) and _sha1_pattern.match(self.branch):
                if self.path:
                    path = f"/{self.owner}/{self.repo}/contributions/{self.branch[:7]}/file/{self.path}"
                else:
                    path = f"/{self.owner}/{self.repo}/contributions/{self.branch[:7]}/file"
            elif self.path:
                path = f"/{self.owner}/{self.repo}/file/{self.path}"
            else:
                path = f"/{self.owner}/{self.repo}/file"
            return str(urlunparse((
                "https",
                "projects.fablabs.io",
                path,
                None,
                None,
                None,
            )))

        else:
            raise ValueError(f"unknown platfrom '{self.platform}'")
