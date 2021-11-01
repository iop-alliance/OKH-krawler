
from typing import Union
import json
import toml
import yaml
import requests
from pathvalidate import sanitize_filename
from krawl.config import WORKDIR
from krawl.licenses import getlicenses


TOML = "toml"
JSON = "json"
YAML = "yml"
BYTES_PER_MB = 1000000

def download(url: str, file_name: str) -> bool:
    try:
        with open(file_name, "wb") as file:
            response = requests.get(url)
            file.write(response.content)
        return True
    except Exception as e:
        print("ERROR Downloading", e)
        return False


def fetch(url: str) -> str:
    try:
        response = requests.get(url)
        return response.text
    except Exception as e:
        print("ERROR Fetching", e)
        return


def parse(s: str, ext: str) -> dict:
    if len(s) > BYTES_PER_MB:
        print("will not read manifests bigger than one MB")
        return ""
    try:
        if ext == TOML:
            return toml.loads(s)
        elif ext == JSON:
            return json.reads(s)
        elif ext == YAML:
            return yaml.safe_load(s)
    except Exception as e:
        print("Failed to parse ...")
        print(" TRACE:", e)
        return None
    else:
        raise ValueError(f"Unknown extension {ext}")


def setversion(manifest: Union[dict, None]):
    if manifest is None:
        return {"version": "unparsable"}
    manifest["version"] = str(manifest.get("version", "0.0"))
    return manifest


def move(dct, ak, bk):
    v = dct.get(ak)
    if v is not None:
        dct[bk] = v
    return dct


def validate(manifest: Union[dict, None]):
    licenses = getlicenses()
    if manifest.get("okhv", "1.0").split(".")[0] == "1":
        # https://github.com/OPEN-NEXT/LOSH/blob/master/Data%20Mapping/data-mapping-OKHv1.md
        manifest["okhv"] = "1.0"
        move(manifest, "title", "name")
        move(manifest, "documentation-home", "repo")
        move(manifest, "archive-download", "release")
        manifest["function"] = (
            manifest.get("description", "")
            + " "
            + manifest.get("intended-use", "")
            + " "
            + manifest.get("health-safety-notice", "")
        )

        otrl = "open-technology-readiness-level"
        if manifest.get("made-independently", False):
            manifest[otrl] = "OTLR-5"
        elif manifest.get("made", False):
            manifest[otrl] = "OTLR-4"
        elif manifest.get("development-stage") == "prototype":
            manifest[otrl] = "OTLR-4"

        m_license = manifest.get("license", {})
        hwl = m_license.get("hardware")
        docl = m_license.get("documentation")
        if hwl is not None:
            if hwl in licenses:
                manifest["spdx-license"] = hwl
            else:
                manifest["alternate-license"] = hwl
        elif docl is not None:
            if docl in licenses:
                manifest["spdx-license"] = docl
            else:
                manifest["alternate-license"] = docl

        licensor = manifest.get("licensor")
        if isinstance(licensor, dict):
            if licensor.get("name") is not None:
                manifest["licensor"] = licensor.get("name")

        makei = manifest.get("making-instructions", {})
        if isinstance(makei, dict) and makei.get("path") is not None:
            manifest["manufacturing-instructions"] = makei.get("path")

        opi = manifest.get("operating-instructions", {})
        if isinstance(opi, dict) and opi.get("path") is not None:
            manifest["user-manual"] = opi.get("path")
    assert isinstance(manifest["repo"], str)
    return manifest


def detailskey(key):
    return f"{key}__details"
