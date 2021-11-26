#!/usr/bin/env python
# coding: utf-8
from datetime import datetime
from krawl.common import detailskey, download, fetch, parse, setversion, validate, sanitize_filename
from krawl.config import GITHUB_KEY, WORKDIR
from krawl.db import (
    Manifest,
    Repo,
    create_repo,
    get_manifest,
    insert,
    migrate,
)
from github import Github, PaginatedList
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlsplit, urlunparse

import re
import sqlite3
import os
from krawl.rdf import make_rdf
import toml
import requests

g = Github(GITHUB_KEY)


def is_okh_manifest_filename(s: str, ext: str) -> bool:
    return s == f"okh.{ext}" or bool(re.match(f"^okh-[\w-]+\.{ext}$", s))


def log(s: str):
    print(s)


GITHUB = "github"

def save(s: str, domain: str, repo: str, version: str, ext: str) -> str:
    dirname = sanitize_filename(repo.replace("/", "____"))
    versionname = sanitize_filename(version.replace(".", "_"))
    dirpath = WORKDIR / "github" / dirname / versionname
    dirpath.mkdir(parents=True, exist_ok=True)
    filepath = dirpath / f"okh.{ext}"
    try:
        with open(filepath, "wb") as file:
            file.write(s.encode("utf8"))
        return dirpath, filepath
    except Exception as e:
        print("ERROR saving", e)
        return False

def getreponame(manifest):
    repourl = manifest.get("repo")
    try:
        reponame = urlparse(manifest.get("repo", "")).path.strip("/")
    except Exception as e:
        print("...couldnt read repo")
        print(e)
        raise Exception('couldnt read repo')
    if len(reponame.split("/")) != 2:
        print(f".... {repourl} is enot a valid repourl")
        raise Exception('is no')
    return reponame


def getcommitsha(manifest):
    reponame = getreponame(manifest)
    repo = g.get_repo(reponame)
    return repo.get_commits()[0].sha


def safe_join(*args):
    stripped = [p.strip("/") for p in args]
    return "/".join(stripped)


RAW = "https://raw.githubusercontent.com"


def setperma(manifest, key, sha):
    fileurl = manifest.get(key)
    repo_name = getreponame(manifest)
    if fileurl is None or repo_name is None:
        return manifest
    if repo_name is None:
        return manifest
    perma = safe_join(RAW, repo_name, sha, fileurl)
    res = requests.head(perma)
    # manifest[key] = /perma
    linkdetails = {"originalURL": fileurl}
    now = datetime()
    if res.ok:
        linkdetails.update({"permaURL": perma})
        linkdetails.update({"lastSeen": f"{now.isoformat()}Z"})
        linkdetails.update({"lastRequested": f"{now.isoformat()}Z"})
    else:
        res = requests.head(fileurl)
        linkdetails.update({"lastSeen": f"{now.isoformat()}Z"})
    path = urlsplit(fileurl).path
    filename = path.split("/")[-1]
    fileparts = filename.split(".")
    if len(fileparts) > 1:
        ext = fileparts[-1]
        linkdetails.update({"fileFormat": ext})
    manifest[detailskey(key)] = linkdetails
    return manifest


def isgithubrepo(manifest):
    try:
        parsed = urlparse(manifest.get("repo", ""))
        return parsed.hostname == "github.com"
    except:
        return False


def makeperma(manifest, value, sha):
    repo_name = getreponame(manifest)
    if repo_name is None or value.startswith("http"):
        return value
    return safe_join(RAW, repo_name, sha, value)


def fetch_gh(ext: str, con: sqlite3.Connection):
    HOSTER = "github.com"
    res = g.search_code(f"filename:okh.{ext}")
    print(f"Searching for okh.{ext}")
    for each in res:
        if not is_okh_manifest_filename(each.name, ext):
            continue
        print("found: ", each.repository.full_name)
        print(" manifest: ", each.name)
        full_name = f"{each.repository.full_name}/{each.name}"
        repo = create_repo(
            Repo(
                hoster=HOSTER,
                url=each.repository.url,
                full_name=each.repository.full_name,
            ),
            con,
        )
        db_manifest = get_manifest(repo.id, each.sha, con)
        if db_manifest is None:
            print("  will download ...")
            stream = fetch(each.download_url)
            manifest = parse(stream, ext)
            manifest = setversion(manifest)

            dirpath, filepath = save(
                stream, GITHUB, f"{full_name}", manifest.get("version"), ext
            )
            print("..saved file", filepath)
            try:
                print("..trying to validate")
                manifest = validate(manifest)
                print("...success validate")
            except Exception as e:
                print("...failure validate.. ")
                print(e)
            try:
                print(each.download_url)
                manifestpath = each.download_url

                manifest["manifest-file"] = manifestpath
                manifest["timestamp"] = each.last_modified
                if isgithubrepo(manifest):
                    commitsha = getcommitsha(manifest)
                    setperma(manifest, "readme", commitsha)
                    setperma(manifest, "image", commitsha)
                    setperma(manifest, "bom", commitsha)
                    setperma(manifest, "manufacturing-instructions", commitsha)
                    setperma(manifest, "user-manual", commitsha)
                    for part in manifest.get("part", []):
                        setperma(part, "source", commitsha)
                        setperma(part, "imge", commitsha)
                        exports = []
                        for export in part.get("export", []):
                            exports.append(makeperma(manifest, export, commitsha))
                        if exports:
                            part["export"] = exports
                manifest['dataSource'] = 'github'
                manifest['repoHost'] = 'github'

                with (dirpath / "normalized.toml").open("wb") as f:
                    f.write(toml.dumps(manifest).encode("utf8"))
                if ext == "toml":
                    print("TOML!")
                print("  download success: ", filepath)
                new_manifest = Manifest(
                    repo_id=repo.id,
                    original_name=each.name,
                    sha=each.sha,
                    download_url=each.download_url,
                    download_success=True,
                    filepath=str(filepath),
                    fileformat=ext,
                )
                insert(new_manifest, con)
                print("created db record")
            except Exception:
                print('error processing...')
            # make_rdf(manifest, dirpath / "okh.ttl")
        else:
            print("  .. already exists")
        print()


if __name__ == "__main__":
    con = sqlite3.connect(
        str(WORKDIR / "crawl.sqlite"), detect_types=sqlite3.PARSE_DECLTYPES
    )
    migrate(con)
    fetch_gh("toml", con)
