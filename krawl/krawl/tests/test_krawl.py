from ..gh import is_okh_manifest_filename
from krawl import __version__


def test_version():
    assert __version__ == "0.1.0"


def test_okh_yml_not():
    assert not is_okh_manifest_filename("asdokh.yml", "yml")


def test_okh_yml_filename():
    assert is_okh_manifest_filename("okh.yml", "yml")


def test_okh_yml_filename_suffix():
    assert is_okh_manifest_filename("okh-hello1.yml", "yml")


def test_okh_yml_filename_suffix_dash():
    assert is_okh_manifest_filename("okh-hello-world.yml", "yml")


def test_okh_yml_filename_suffix_underscore():
    assert is_okh_manifest_filename("okh-hello_world.yml", "yml")


def test_okh_yml_filename_suffix_unicode():
    assert is_okh_manifest_filename("okh-hello_wörld.yml", "yml")
