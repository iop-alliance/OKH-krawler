#!/usr/bin/env python
# coding: utf-8
import json
from os import pathconf, sysconf
from krawl.licenses import getlicenseblacklists, getlicenses
from krawl.wf import make_version
import toml


def makerepo(dct):
    # TODO
    # > It's not possible to query a canonical URL from the API right now.
    # >
    # >
    # >
    # > These are the formats for:
    # >
    # > - Profiles: @slug
    # >
    # > - Organization: +slug
    # >
    # > - Project: parentSlug/slug
    # >
    # >
    # >
    # > parentSlug is a profile or organization slug. It can be queried as a field of Project.
    # >
    # prefixes = {
    #     "Project": "@",
    #     "Content": "+",
    # }
    # typename = dct["space"]["content"]["__typename"]
    # if typename not in prefixes.keys():
    #     print("[WF][MakeRepo] ", typename, " not found in repo prefix matcher")
    # prefix = prefixes.get(typename, "@")
    # stem = dct["space"]["content"]["slug"]
    prefix = ""
    try:
        stem = dct["creatorProfile"]["username"]
        leaf = dct["slug"]
        return f"https://wikifactory.com/{prefix}{stem}/{leaf}"
    except KeyError:
        print("couldt get creator profile:")
        print(dct)
        return ""


FORBIDDEN = -1


def get_license(dct):
    valid = getlicenses()
    license = dct.get("license", {})
    if license is None:
        return None
    license = license.get("abreviation", "na")
    if license not in valid:
        print("[WF/LicenseMatching] ", license, " is not valid spdx")
        return None
    blacklist = getlicenseblacklists()
    if license in blacklist:
        print("[WF/LicenseMatching] ", license, " is forbidden, will drop")
        return None
    return f"https://spdx.org/licenses/{license}"
    return license


def getfunction(dct):
    desc = dct.get("description", "").replace("<p>", "").replace("</p>", "\n").strip()
    if desc == "":
        return None
    return desc


from langdetect import detect


def getlang(dct):
    desc = dct.get("description", "")
    if desc == "":
        return None
    if len(desc.split(" ")) <= 2:
        return "en"
    else:
        lang = detect(desc)
        return lang


def getfiles(dct, check):
    files = []
    if dct.get("contributionUpstream") is None:
        return None
    for file in dct.get("contributionUpstream", {}).get("files", []):
        inner = file.get("file")
        if inner is None:
            continue
        if inner.get("permalink") is None:
            continue
        name = str(Path(file['dirname']) / Path(file['filename']))
        partname = file['filename'].split('.')[0]
        ext = file['filename'].split('.')[-1].lower()
        if name != "README.md" and check(ext):
            dct = {
                    "name": partname,
                    "permalink": inner["permalink"],
                    "mimetype": inner["mimeType"],
                    "ext": ext
                }

            if check(ext):
                export = f"{name}_export"
            files.append(dct)
    if files == []:
        return None
    else:
        return files

PARTEXTENSIONS = [
"3dm",
"3dxml",
"3KO",
"3mf",
"amf",
"asab",
"asat",
"asm",
"CATPart",
"CATProduct",
"CGR",
"csg",
"dae",
"dgn",
"dwg",
"dxf",
"fcstd",
"html",
"iam",
"iges",
"igs",
"ipt",
"iwb",
"iwp",
"jt",
"j_t",
"model",
"obj",
"off",
"par",
"pdf",
"ply",
"pod",
"prc",
"prt",
"psm",
"sab",
"sat",
"scad",
"sldasm",
"sldprt",
"sms",
"step",
"stl",
"stp",
"svg",
"u3d",
"vda",
"wrl",
"x_t",
"xcgm",
]
def getparts(dct):
    def ispart(ext):
        return ext in PARTEXTENSIONS
    return [dict(
        name=f['name'],
        export=[dict(fileFormat=f['ext'], fileUrl=f['permalink'])])  for f in getfiles(dct, ispart)]

def getimage(dct):
    if dct.get("image") is None:
        return None
    else:
        return dct.get("image").get("permalink", None)

def getimagedetails(dct):
    img = getimage(dct)
    if img is None:
        return None
    return dict(
        originalUrl=img,
        permaUrl=img,
    )


def getreadme(dct):
    files = dct.get("contributionUpstream", {})
    if files is None:
        return None
    cf = files.get("contribFile", {})
    if cf is None:
        return None
    file = cf.get("file", {})
    if file is None:
        return None
    pl = file.get("permalink", None)
    return pl

def getreadmedetails(dct):
    readme = getreadme(dct)
    if readme is None:
        return None
    return dict(
        originalUrl=readme,
        permaUrl=readme,
        fileFormat="md",
    )


def convert(dct):
    return {
        "name": dct.get("name"),
        "dataSource": "Wikifactory",
        "repoHost": "Wikifactory",
        "repo": makerepo(dct),
        "version": make_version(dct),
        "spdx-license": get_license(dct),
        "licensor": dct.get("creatorProfile", {}).get("fullName"),
        "readme": getreadme(dct),
        "readme__details": getreadmedetails(dct),
        "documentation-language": getlang(dct),
        "image": getimage(dct),
        "image__details": getimagedetails(dct),
        "function": getfunction(dct),
        "part": getparts(dct),
    }

def isrelevant(rec):
    has_license = rec['spdx-license'] is not None
    has_readme = rec['readme'] is not None
    has_files = rec['part'] is not None or rec['export'] is not None
    # return has_license and has_readme and has_files
    return True

import argparse
from pathlib import Path

if __name__ == "__main__":
    # argv = sysconf.argv[1:]
    # args = argparser.parse_args(argv)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files", metavar="files", help="filepaths to process", nargs="+"
    )
    args = parser.parse_args()
    print("Starting WF convert")
    for file in args.files:
        file = Path(file)
        with open(file, "r") as f:
            data = json.load(f)
        print("[WF] Converting: ", str(file))
        normalized = convert(data)
        relevant = isrelevant(normalized)
        if relevant:
            with (file.parent / "normalized.toml").open("wb") as f:
                f.write(toml.dumps(normalized).encode("utf8"))
            print("[WF]     success. ", str(file))
        else:
            print("[WF]    skipping. ", str(file))
