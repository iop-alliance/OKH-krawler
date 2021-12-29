from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import validators

from krawl.fetcher.factory import FetcherFactory
from krawl.project import Project
from krawl.validator import Validator, _known_languages, non_zero_length_string, version


class StrictValidator(Validator):

    def validate(self, project: Project) -> tuple[bool, list[str]]:
        reasons = []
        # meta data
        reasons.extend(self._validate_string("meta.source", project.meta.source))
        if project.meta.source and not FetcherFactory.is_fetcher_available(project.meta.source):
            reasons.append(f"no fetcher for '{project.meta.source}' available")
        reasons.extend(self._validate_string("meta.host", project.meta.host))
        reasons.extend(self._validate_string("meta.owner", project.meta.owner, min=3, max=256))
        reasons.extend(self._validate_string("meta.repo", project.meta.repo, min=3, max=256))

        # spec conformance
        reasons.extend(self._validate_string("name", project.name, min=3, max=256))
        reasons.extend(self._validate_url("repo", project.repo))
        # reasons.extend(self._validate_url("image", project.image, missing_ok=True))
        reasons.extend(self._validate_string("functional description", project.function, min=1, max=100000))
        reasons.extend(self._validate_string("licensor", project.licensor, min=3, max=256))
        reasons.extend(self._validate_string("organization", project.organization, min=3, max=256, missing_ok=True))
        # reasons.extend(self._validate_url("readme", project.readme))
        # reasons.extend(self._validate_in_list("language code", project.documentation_language, _known_languages)) #TODO: need to add more codes

        if not non_zero_length_string(project.version):
            reasons.append("missing version")
        # FIXME: version validation is deactivated for now
        # elif not version(project.version):
        #     reasons.append("invalid version")

        if not project.license:
            reasons.append("missing license")
        elif project.license.is_blocked:
            reasons.append(f"'{project.license}' is not a conformant license")

        if not isinstance(project.part, list):
            reasons.append("part must be of type list")
        elif not isinstance(project.part, list):
            reasons.append("must have at least one part")

        if reasons:
            return False, reasons
        return True, None

    @staticmethod
    def _validate_in_list(title: str, value: Any, in_: Iterable, missing_ok=False) -> list[str]:
        if value is None:
            if missing_ok:
                return []
            return [f"missing {title}"]
        if not value in in_:
            return [f"{title} '{value}' is unknown"]
        return []

    @staticmethod
    def _validate_string(title: str, string: str, min=None, max=None, missing_ok=False) -> list[str]:
        if string is None:
            if missing_ok:
                return []
            return [f"missing {title}"]
        if not isinstance(string, str):
            return [f"{title} must be of type string"]
        if min is not None and len(string) < min:
            return [f"{title} is to short (<{min})"]
        if max is not None and len(string) > max:
            return [f"{title} is to long (>{max})"]
        return []

    @staticmethod
    def _validate_url(title: str, url: str, missing_ok=False) -> list[str]:
        if url is None:
            if missing_ok:
                return []
            return [f"missing {title}"]
        if not isinstance(url, str):
            return [f"{title} must be of type string"]
        if not validators.url(url):
            return [f"{title} must be a valid URL"]
        return []
