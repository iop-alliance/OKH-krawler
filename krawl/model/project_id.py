from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ProjectId:
    """ProjectId serves as an identifier for projects, that can be used by the
    appropriate fetcher to fetch the projects metadata.

    Args:
        platform (str): The domain of the platform.
        owner (str): User or group that owns the project.
        repo (str): Name of the project repository.
        path (str): Canonical path of the manifest file inside the repository, if any.
    """

    # platform: str
    # owner: str
    # repo: str
    # path: str = None
    uri: str

    def __str__(self) -> str:
        # if self.path:
        #     return f"{self.platform}/{self.owner}/{self.repo}/{self.path}"
        # return f"{self.platform}/{self.owner}/{self.repo}"
        return self.uri

    @classmethod
    def from_url(cls, url: str) -> ProjectId:
        # pu = PlatformURL.from_url(url)

        # # if pu.platform == "oshwa.org":
        # #     pu.owner = 'none'

        # if not pu.owner:
        #     raise ValueError(f"could not extract owner from URL '{url}'")
        # if not pu.repo:
        #     raise ValueError(f"could not extract repo from URL '{url}'")

        # path_str = None
        # if pu.path:
        #     path_str = str(pu.path)

        # return cls(platform=pu.platform, owner=pu.owner, repo=pu.repo, path=path_str)
        return cls(uri=url)
