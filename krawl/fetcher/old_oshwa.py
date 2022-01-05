import datetime
import json
import math
import urllib.parse

import requests

# Bearer Token Authentication
import toml
from pathvalidate import sanitize_filename

from krawl.config import OSHWA_TOKEN, WORKDIR
import dateutil.parser

ENDPOINT = "https://certificationapi.oshwa.org/api/projects"
STROAGE_DIR = WORKDIR / "oshwa"


def fetch(page=1):
    headers = {
        'Authorization': 'Bearer ' + OSHWA_TOKEN
    }

    offset = 1000
    if page > 1:
        offset = page * 1000 - 1000

    response = requests.request('GET', ENDPOINT, headers=headers, params={'limit': 1000, 'offset': offset})

    if response.status_code > 205:
        print(response.text)
        return False

    data = response.json()

    pages = math.ceil(data['total'] / data['limit'])

    for item in data['items']:
        print(f"Convert item {item.get('projectName')}..")
        mapped_data = convert(item)
        filepath = make_file_dir(item)
        write_toml(filepath, mapped_data)
        write_json(filepath, item)

        print('File saved to ' + str(filepath))

    if page < pages:
        fetch(page=page + 1)


def make_version(dct):
    try:
        lastmodified = dateutil.parser.isoparse(dct["certificationDate"])
    except KeyError:
        lastmodified = dateutil.parser.isoparse(datetime.datetime.now().isoformat())

    return lastmodified.strftime("%Y%m%d%H%M%S")


def write_json(filepath, dct):
    with (filepath / "raw.json").open("wb") as f:
        f.write(json.dumps(dct).encode('utf-8'))
        return True


def make_file_dir(dct):
    dirname = sanitize_filename(dct["oshwaUid"] + "____" + dct["projectName"])
    version = make_version(dct)
    dirpath = STROAGE_DIR / dirname / version
    dirpath.mkdir(parents=True, exist_ok=True)
    return dirpath


def write_toml(filepath, mapped_data):
    with (filepath / "normalized.toml").open("wb") as f:
        f.write(toml.dumps(mapped_data).encode("utf8"))
        return True


def convert(dct):
    spdx_license = dct.get('hardwareLicense')
    if spdx_license == "Other":
        # TODO: may be entry
        spdx_license = "alternativeLicense"

    return {
        "name": dct.get("projectName"),
        "dataSource": "OSHWA",
        "repoHost": extract_repo_host(dct.get("documentationUrl")),
        "repo": dct.get("documentationUrl"),
        "version": dct.get("projectVersion"),
        "spdx-license": spdx_license,
        "licensor": dct.get("responsibleParty"),
        "cpc-classification": get_classification(dct),
        "function": dct.get("projectDescription")
    }


def extract_repo_host(docUrl):
    url = urllib.parse.urlparse(docUrl)
    return url.hostname


def get_classification(dct):
    primary_type = dct.get("primaryType")
    additional_type = dct.get("additionalType")

    unmappable_categories = [
        "Arts",
        "Education",
        "Environmental",
        "Manufacturing",
        "Other",
        "Science",
        "Tool"
    ]

    if primary_type in unmappable_categories:
        if additional_type is None:
            return ""
        if len(additional_type) == 0:
            return ""
        else:
            return additional_type

    mapping_primary_to_cpc = {
        "3D Printing": "B33Y",
        "Agriculture": "A01",
        "Electronics": "H",
        "Enclosure": "F16M",
        "Home Connection": "H04W",
        "IOT": "H04",
        "Robotics": "B25J9 / 00",
        "Sound": "H04R",
        "Space": "B64G",
        "Wearables": "H"
    }

    try:
        cpc = mapping_primary_to_cpc[primary_type]
        return cpc
    except KeyError:
        return primary_type
