from functools import lru_cache

import requests


@lru_cache()
def getlicenses():
    res = requests.get("https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json")
    elems = res.json()["licenses"]

    # res = requests.get("https://raw.githubusercontent.com/OPEN-NEXT/LOSH-Licenses/main/SPDX-allowlist.json")
    # elems_losh = res.json()
    # elems.extend(elems_losh)
    l = {l["licenseId"] for l in elems}
    return l


@lru_cache()
def getlicenseblacklists():
    res = requests.get(
        # NOTE TODO FIXME This list was available under the original URL:
        # https://raw.githubusercontent.com/OPEN-NEXT/LOSH/master/Data%20Mapping/SPDX-blacklist"
        # in one-column CSV format (which is what this code here assumes),
        # but has since moved to
        # https://raw.githubusercontent.com/OPEN-NEXT/LOSH-Licenses/main/SPDX-blocklist.json
        # and been converted to JSON.
        # Thus, this code is broken at the moment.
        # My (hoijui) goal is, to get it available as CSV again;
        # see issue:
        # https://github.com/OPEN-NEXT/LOSH-Licenses/issues/1#issuecomment-963914298
        "https://raw.githubusercontent.com/OPEN-NEXT/LOSH/master/Data%20Mapping/SPDX-blacklist")
    elems = res.text.strip().split("\n")
    license_id = {elem.strip() for elem in elems}
    return license_id


if __name__ == "__main__":
    print(getlicenses())
