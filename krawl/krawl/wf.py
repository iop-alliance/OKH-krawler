#!/usr/bin/env python
# coding: utf-8
from pathlib import Path
from krawl.config import WORKDIR
import requests
from pprint import pprint
from pathvalidate import sanitize_filename
import dateutil.parser
import json
import os

headers = {"User-Agent": "oshi-krawl", "From": "alec@konek.to"}
URL = "https://wikifactory.com/api/graphql"


def isvalid(node):
    # return (
    #     node["license"] is not None
    #     and node["image"] is not None
    #     # and node["contributionUpstream"] is not None
    #     # and node["contributionUpstream"].get("contribFile") is not None
    #     # and node["contributionUpstream"].get("contribFile", {}).get("filename", "")
    #     # == "README.md"
    # )
    return True

    # and node['contributionUpstream']['contribFile']['files'] is not None
    # and len(node['contributionUpstream']['contribFile']['files']) > 0)


query = """
query Project($batchSize: Int, $cursor: String) {
  projects(first: $batchSize, after: $cursor) {
		result {
      pageInfo {
        hasNextPage
        startCursor
        endCursor
      }
      edges {
    	node {
        id
        name
        slug
        lastActivityAt
        license {
            name
            title
            abreviation
        }
        image {
            permalink
        }
        creatorProfile {
            fullName
            username
        }
        space {
            id
            content {
                slug
                __typename
            }
        }
      description
      contributionUpstream {
        contribFile(filepath: "README.md") {
          dirname
          filename
          isFolder
                    file {
            permalink
          }
        }
        files {
          filename
          dirname
          contribution {
            version
          }
          file {
            mimeType
            permalink
          }
        }
      }
      }
    }
   }
  }
}
"""

WF_WORKDIR = WORKDIR / "wikifactory"


def make_version(dct):
    lastmodified = dateutil.parser.isoparse(dct["lastActivityAt"])
    return lastmodified.strftime("%Y%m%d%H%M%S")


def saveraw(dct: dict, storagedir: Path) -> str:
    dirname = sanitize_filename(dct["space"]["content"]["slug"] + "____" + dct["name"])
    version = make_version(dct)
    dirpath = storagedir / dirname / version
    dirpath.mkdir(parents=True, exist_ok=True)
    filepath = dirpath / f"record.json"
    try:
        with open(filepath, "w") as file:
            json.dump(dct, file, indent=2, sort_keys=True)
        return dirpath, filepath
    except Exception as e:
        print("ERROR saving", e)
        return False


def fetch_wf(storagedir):
    cursor = ""
    has_next_page = True
    max_pages = int(os.environ.get("MAX_WF_PAGES", "999999"))
    curr_page = 0
    print("init wf fetch")
    with requests.Session() as session:
      while has_next_page and curr_page < max_pages:
          print("curr page:", curr_page)
          print("cursor: ", cursor)
          r = session.post(
              URL,
              json={"query": query, "variables": {"cursor": cursor, "batchSize": 50}},
              headers=headers,
              timeout=10
          )
          # r = requests.post(url, json={'query': q2 })
          if not r.ok:
              print(
                  f"couldnt fetch wikifactory code: {r.status_code}, (cursor: {cursor})"
              )
              return
          print(f"status: {r.status_code}")
          payload = r.json()
          try:
              result = payload["data"]["projects"]["result"]
              nodes = [d["node"] for d in result["edges"]]
          except Exception as e:
              print("Could read payload: ")
              pprint(payload)
              raise e
          pageinfo = result["pageInfo"]
          cursor = pageinfo["endCursor"]
          for each in nodes:
              if isvalid(each):
                  filepath = saveraw(each, storagedir)

                  print("saved: ", filepath)
          curr_page += 1
          has_next_page = pageinfo["hasNextPage"]
          if not has_next_page:
            print("last page was ", cursor)


if __name__ == "__main__":
    # Execute the parse_args() method
    fetch_wf(WF_WORKDIR)