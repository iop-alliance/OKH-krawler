from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import validators

from krawl.project import File, Project
from krawl.validator import Validator, is_bcp_47_language_tag, is_non_zero_length_string, is_okh_version, is_version


class StrictValidator(Validator):

    def validate(self, project: Project) -> tuple[bool, list[str]]:
        reasons = []

        if not is_non_zero_length_string(project.okhv):
            reasons.append("missing okhv")
        elif not is_okh_version(project.okhv):
            reasons.append(f"invalid okhv '{project.okhv}'")
        reasons.extend(_validate_string("name", project.name, min=1, max=256))
        reasons.extend(_validate_url("repo", project.repo))
        reasons.extend(_validate_file("image", project.image, missing_ok=True))
        reasons.extend(_validate_string("functional description", project.function, min=1, max=100000))
        reasons.extend(_validate_string("licensor", project.licensor, min=1, max=256))
        reasons.extend(_validate_string("organization", project.organization, min=1, max=256, missing_ok=True))
        reasons.extend(_validate_file("readme", project.readme, missing_ok=True))
        reasons.extend(_validate_file("bom", project.bom, missing_ok=True))
        reasons.extend(_validate_file("manufacturing_instructions", project.manufacturing_instructions,
                                      missing_ok=True))
        reasons.extend(_validate_file("user_manual", project.user_manual, missing_ok=True))

        if not is_non_zero_length_string(project.documentation_language):
            reasons.append("missing documentation language")
        elif not is_bcp_47_language_tag(project.documentation_language):
            reasons.append(f"invalid language tag '{project.documentation_language}'")

        if not is_non_zero_length_string(project.version):
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


def _validate_in_list(title: str, value: Any, in_: Iterable, missing_ok=False) -> list[str]:
    if value is None:
        if missing_ok:
            return []
        return [f"missing {title}"]
    if not value in in_:
        return [f"{title} '{value}' is unknown"]
    return []


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


def _validate_file(title: str, file: File, missing_ok=False) -> list[str]:
    if file is None:
        if missing_ok:
            return []
        return [f"missing {title}"]
    if not isinstance(file, File):
        return [f"{title} must be of type file"]

    reasons = []
    reasons.extend(_validate_string(title + ".name", file.name, min=1, max=256))
    reasons.extend(_validate_url(title + ".url", file.url, missing_ok=True))
    reasons.extend(_validate_url(title + ".frozen_url", file.frozen_url, missing_ok=True))
    #TODO: validate other fields of files

    return reasons
