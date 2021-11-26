import requests
from functools import lru_cache


@lru_cache()
def getlicenses():
    res = requests.get(
        "https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json"
    )
    elems = res.json()["licenses"]

    # res = requests.get("https://raw.githubusercontent.com/OPEN-NEXT/LOSH-Licenses/main/SPDX-allowlist.json")
    # elems_losh = res.json()
    # elems.extend(elems_losh)
    l = {l["licenseId"] for l in elems}
    return l


@lru_cache()
def getlicenseblacklists():
    res = requests.get(
        "https://raw.githubusercontent.com/OPEN-NEXT/LOSH/master/Data%20Mapping/SPDX-blacklist"
    )
    elems = res.text.strip().split("\n")
    l = {e.strip() for e in elems}
    return l


if __name__ == "__main__":
    print(getlicenses())
