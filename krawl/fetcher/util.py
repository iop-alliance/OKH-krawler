from __future__ import annotations

import os
import re
import sys
from pathlib import Path
import subprocess
import tempfile

from krawl.log import get_child_logger
from krawl.errors import ConversionError

log = get_child_logger("util")

_manifest_name_pattern = r"^okh([_\-\t ].+)*$"


def is_accepted_manifest_file_name(path: Path) -> bool:
    """Return true if the given file name matches an accepted manifest name."""
    return bool(re.match(_manifest_name_pattern, path.with_suffix("").stem))


def is_empty(content: str | bytes) -> bool:
    """Return true if the given content is empty."""
    return not bool(content)


def is_binary(content: str | bytes) -> bool:
    """Return true if the given content is binary."""
    if isinstance(content, str):
        return "\0" in content
    return b"\0" in content

def _recuperate_invalid_yaml_manifest(manifest_contents: bytes) -> bytes:
    """Cleans up OKH v1 (YAMl) manifest content.
    Many manifests out there use bad syntax or invalid values,
    which we try to undo as much as possible in here."""

    (_, fn_v1) = tempfile.mkstemp()
    # Target file should not yet exist when converting
    os.remove(fn_v1)

    with open(fn_v1, "wb") as binary_file:
        binary_file.write(manifest_contents)

    sanitize_okh_v1_yaml(fn_v1)

    with open(fn_v1, "rb") as binary_file:
        manifest_contents = binary_file.read()
        os.remove(fn_v1)
        return manifest_contents

def sanitize_okh_v1_yaml(manifest_file: Path):
    """Sanitizes an OKH v1 (YAMl) manifest,
    using the external software 'sanitize-v1-yaml'
    from the okh-tool repo."""

    conv_cmd = ['sanitize-v1-yaml', '--in-place', manifest_file]
    # res = subprocess.run(conv_cmd)
    try:
        subprocess.check_output(conv_cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        raise ConversionError(f"Failed to sanitize OKH v1 manifest, exitcode: {err.returncode}, stderr: {err.stderr.decode(sys.getfilesystemencoding())}, stdout: {err.output.decode(sys.getfilesystemencoding())}", [])

def convert_okh_v1_to_losh(manifest_contents: bytes) -> bytes | None:
    """Converts OKH v1 (YAMl) manifest contents to OKH LOSH (TOML) manifest contents,
    using the external software 'okh-tool'."""

    manifest_contents = _recuperate_invalid_yaml_manifest(manifest_contents)

    (_, fn_v1) = tempfile.mkstemp()
    (_, fn_losh) = tempfile.mkstemp()
    # Target file should not yet exist when converting
    os.remove(fn_losh)

    with open(fn_v1, "wb") as binary_file:
        binary_file.write(manifest_contents)

    conv_cmd = ['okh-tool', 'conv', fn_v1, fn_losh]
    try:
        subprocess.check_output(conv_cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        raise ConversionError(f"Failed to convert OKH v1 manifest to OKH LOSH, exitcode: {err.returncode}, stderr: {err.stderr.decode(sys.getfilesystemencoding())}, stdout: {err.output.decode(sys.getfilesystemencoding())}", [])

    # res.check_returncode()
    with open(fn_losh, "rb") as binary_file:
        manifest_contents = binary_file.read()

    if os.path.exists(fn_v1):
        os.remove(fn_v1)
    if os.path.exists(fn_losh):
        os.remove(fn_losh)

    return manifest_contents
