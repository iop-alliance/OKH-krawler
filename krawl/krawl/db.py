import sqlite3
from sqlite3 import Connection
from typing import NamedTuple, Optional

sqlite3.register_adapter(bool, int)


def parse_db_bool(v: str) -> bool:
    i = int(v)
    b = bool(i)
    return b


sqlite3.register_converter("BOOLEAN", parse_db_bool)


def migrate(con: sqlite3.Connection):
    cur = con.cursor()
    repos_sql = """
    create table if not exists repos (
        id integer primary key,
        hoster text,
        url text,
        full_name text,
        unique (hoster, full_name)
    )"""
    cur.execute(repos_sql)

    manifests = """
    create table if not exists manifests (
        id integer primary key,
        repo_id integer,
        original_name text,
        sha text,
        download_url text,
        download_success boolean,
        filepath text,
        fileformat text,
        unique(repo_id, sha),
        foreign key (repo_id) references repos (id)
    )
    """
    cur.execute(manifests)


class Repo(NamedTuple):
    hoster: str
    url: str
    full_name: str
    id: Optional[int] = None


Repo._table = "repos"


class Manifest(NamedTuple):
    repo_id: int
    original_name: str
    sha: str
    download_url: str
    download_success: bool
    filepath: str
    fileformat: str
    id: Optional[int] = None


Manifest._table = "manifests"


def remove_id(tup):
    return tuple(tup[:-1])


def insert(tup: NamedTuple, con: sqlite3.Connection):
    c = con.cursor()
    fields = [f for f in tup.__class__._fields if f != "id"]
    fields_q = ", ".join(fields)
    qs_q = ", ".join(["?" for f in fields])
    table = tup.__class__._table
    c.execute(f"""insert into {table} ({fields_q}) values ({qs_q})""", remove_id(tup))
    con.commit()


def get_repo(r: Repo, con):
    cur = con.cursor()
    res = cur.execute(
        "select hoster, url, full_name, id from repos where url = ?", (r.url,)
    )
    found = list(res.fetchall())
    if len(found) >= 1:
        if len(found) > 1:
            print("found more than one matching repo..")
        return Repo(*found[0])
    else:
        return None


def create_repo(r: Repo, con: sqlite3.Connection):
    """ return true if created other, false if alrady exists """
    found = get_repo(r, con)
    if found is not None:
        return found
    else:
        try:
            insert(r, con)
            return get_repo(r, con)
        except sqlite3.IntegrityError as e:
            if str(e).find("UNIQUE constraint failed") != -1:
                return False
            else:
                raise e


def get_manifest(repo_id: int, sha: str, con: sqlite3.Connection) -> Optional[Manifest]:
    cur = con.cursor()
    select_q = f"""select {", ".join(Manifest._fields)} from manifests where repo_id = ? and sha = ?"""
    res = cur.execute(select_q, (repo_id, sha))
    found = list(res.fetchall())
    if len(found) == 0:
        return None
    return Manifest(*found[0])


if __name__ == "__main__":
    import tempfile

    con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
    # con.row_factory = sqlite3.Row
    migrate(con)
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(cur.fetchall())
    print(create_repo(Repo(hoster="github.com", full_name="aaa"), con))
    repo = create_repo(Repo(hoster="github.com", full_name="aaa"), con)
    print(repo)
    insert(
        Manifest(
            repo_id=repo.id,
            original_name="orignal_name",
            sha="aaa",
            download_url="download_irl",
            download_success=False,
            filepath="filepath",
            fileformat="yml",
        ),
        con,
    )
    insert(
        Manifest(
            repo_id=repo.id,
            original_name="orignal_name",
            sha="aaaa",
            download_url="download_irl",
            download_success=True,
            filepath="filepath",
            fileformat="yml",
        ),
        con,
    )

    manifest = get_manifest(repo.id, "aaa", con)
    print(manifest)
    manifest = get_manifest(repo.id, "aaaa", con)
    assert type(manifest.download_success) == bool
    print(manifest)

    manifest_notfound = get_manifest(repo.id, "bbb", con)
    print(manifest_notfound)