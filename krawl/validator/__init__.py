from __future__ import annotations

import re

import validators

from krawl.project import Project

# see https://semver.org
_semver_pattern = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-((?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
_sha1_pattern = re.compile(r"^[A-Fa-f0-9]{40}$")
_sha256_pattern = re.compile(r"^[A-Fa-f0-9]{64}$")
_known_languages = [
    "af", "ar", "bg", "bn", "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "fa", "fi", "fr", "gu", "he", "hi",
    "hr", "hu", "id", "it", "ja", "kn", "ko", "lt", "lv", "mk", "ml", "mr", "ne", "nl", "no", "pa", "pl", "pt", "ro",
    "ru", "sk", "sl", "so", "sq", "sv", "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi", "zh-cn", "zh-tw"
]


@validators.utils.validator
def version(value):
    """Return whether or not given value is a valid semantic version."""
    # check if it is a semantic version
    result = _semver_pattern.match(value)
    if result:
        return True

    # check if it is a sha1 hash
    result = _sha1_pattern.match(value)
    if result:
        return True

    # check if it is a sha256 hash
    result = _sha256_pattern.match(value)
    if result:
        return True

    # doesn't match any accepted patterns
    return False


@validators.utils.validator
def non_zero_length_string(value):
    """Return whether or not given value is a string with at least one character."""
    return isinstance(value, str) and value


@validators.utils.validator
def max_length(value, max):
    """Return whether or not given value is a string with max length."""
    return isinstance(value, str) and len(value) <= max


class Validator:

    def validate(self, project: Project) -> tuple[bool, list[str]]:
        raise NotImplementedError()
