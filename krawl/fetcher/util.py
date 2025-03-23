# SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
# SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import tomli
import yaml

from krawl.errors import ConversionError
from krawl.log import get_child_logger

log = get_child_logger("util")

# _manifest_name_pattern = r"^okh([_\-\t ].+)*$"
_manifest_name_pattern = r"^(.+\.)?okh([_\-:.][0-9a-zA-Z:._\-]+)?$"
_manifest_suffix_pattern = r"^\.(json|toml|ya?ml)$"


def is_accepted_manifest_file_name(path: Path) -> bool:
    """Return true if the given file name matches an accepted manifest name."""
    return bool(re.match(_manifest_name_pattern, path.stem)) and bool(re.match(_manifest_suffix_pattern, path.suffix))


def is_empty(content: str | bytes) -> bool:
    """Return true if the given content is empty."""
    return not bool(content)


def is_binary(content: str | bytes) -> bool:
    """Return true if the given content is binary."""
    if isinstance(content, str):
        return "\0" in content
    return b"\0" in content


def recuperate_invalid_yaml_manifest(manifest_contents: bytes) -> bytes:
    """Cleans up OKH v1 (YAMl) manifest content.
    Many manifests out there use bad syntax or invalid values,
    which we try to undo as much as possible in here."""

    fn_v1: Path = Path(tempfile.mkstemp()[1])
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

    conv_cmd: list[str] = ['sanitize-v1-yaml', '--in-place', str(manifest_file)]
    # res = subprocess.run(conv_cmd)
    try:
        subprocess.check_output(conv_cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        raise ConversionError(
            "Failed to sanitize OKH v1 manifest,"
            f" exitcode: {err.returncode},"
            f" stderr: {err.stderr.decode(sys.getfilesystemencoding())},"
            f" stdout: {err.output.decode(sys.getfilesystemencoding())}", []) from err


def convert_okh_v1_to_losh(manifest_contents: bytes) -> bytes:
    """Converts serialized (bytes) OKH v1 (YAMl) manifest contents
    to serialized (bytes) OKH LOSH (TOML) manifest contents,
    using the external software 'okh-tool'."""

    # manifest_contents = recuperate_invalid_yaml_manifest(manifest_contents)

    (_, fn_v1) = tempfile.mkstemp()
    (_, fn_losh) = tempfile.mkstemp()
    # Target file should not yet exist when converting
    os.remove(fn_losh)

    with open(fn_v1, "wb") as binary_file:
        binary_file.write(manifest_contents)

    conv_cmd = ['okh-tool', 'conv', fn_v1, fn_losh]
    try:
        log.debug('Going to run command "%s" ...', " ".join(conv_cmd))
        subprocess.check_output(conv_cmd, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        sep = "-" * 80
        raise ConversionError("Failed to convert OKH v1 manifest to OKH LOSH,\n"
                              f"* exitcode: {err.returncode}\n"
                              f"* input:\n{sep}\n{manifest_contents.decode(sys.getfilesystemencoding())}\n{sep}\n"
                              # f"* stdout:\n{sep}\n{err.output.decode(sys.getfilesystemencoding())}\n{sep}\n"
                              f"* stderr:\n{sep}\n{err.stderr.decode(sys.getfilesystemencoding())}\n{sep}") from err

    log.debug('done.')
    log.debug('Should have written file "%s".', fn_losh)

    # res.check_returncode()
    with open(fn_losh, "rb") as binary_file:
        manifest_contents = binary_file.read()
    log.debug('Read file "%s".', fn_losh)

    if os.path.exists(fn_v1):
        os.remove(fn_v1)
    if os.path.exists(fn_losh):
        os.remove(fn_losh)

    return manifest_contents


def convert_okh_v1_dict_to_losh(manifest_contents: dict) -> dict:
    """Converts deserialized OKH v1 (YAML) manifest contents
    to deserialized OKH LOSH (TOML) manifest contents,
    using the external software 'okh-tool'."""

    manifest_contents_yaml: str = yaml.dump(data=manifest_contents, stream=None)
    print("YYY")
    print(manifest_contents_yaml)
    print("YYY")
    # tst_yaml_file = 'tst.yml'
    # yaml.dump(data=manifest_contents, stream=tst_yaml_file)
    manifest_contents_toml: bytes = convert_okh_v1_to_losh(manifest_contents_yaml.encode('utf-8'))
    # print(manifest_contents_toml.decode('utf-8'))
    # tst_toml_file = 'tst.toml'
    # manifest_contents_losh: dict = toml.load(tst_toml_file)
    print("XXX")
    print(manifest_contents_toml.decode('utf-8'))
    print("XXX")
    manifest_contents_losh: dict = tomli.loads(manifest_contents_toml.decode('utf-8'))

    return manifest_contents_losh
