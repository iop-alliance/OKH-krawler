from urllib.parse import urlparse

from krawl.gh import getcommitsha, isgithubrepo, setperma


def test_makeperma():
    manifest = {"repo": "https://github.com/ahane/krawler-test", "readme": "README.md"}

    manifest = setperma(manifest, "readme", getcommitsha(manifest))
    assert manifest["readme__status"]


def test_makeperma_status():
    manifest = {
        "repo": "https://github.com/ahane/krawler-test",
        "readme": "DOESNTEXIST.md",
    }

    manifest = setperma(manifest, "readme", getcommitsha(manifest))
    assert not manifest["readme__status"]


def test_makeperma_urls():
    manifest = {
        "repo": "https://gitlab.com/ahane/krawler-test",
        "readme": "https://raw.githubusercontent.com/ahane/krawler-test/master/README.md",
    }
    manifest = setperma(manifest, "readme", getcommitsha(manifest))
    print(manifest["readme"])
    print(manifest["readme__status"])
    assert manifest["readme__status"]


def test_isgithubrepo():
    parsed = urlparse("https://github.com/ahane/krawler-test")
    print("HHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHH")
    print(parsed.hostname)
    assert isgithurepo("https://github.com/ahane/krawler-test")
