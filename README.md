# LOSH-Krawler

---
---

!!!
**DEPRECATED**
This repo is now deprecated,
and superseded by <https://github.com/iop-alliance/OKH-krawler>.
!!!

---
---

<s>


This is a first implementation of the crawler for the [Library of Open Source Hardware (LOSH)](https://losh.opennext.eu). The crawler searches [Wikifactory](https://wikifactory.com) and [GitHub](https://github.com) for hardware projects, that comply with the [OKH-LOSH specification](https://github.com/OPEN-NEXT/OKH-LOSH). Once such a project is found, its metadata is downloaded, parsed and sanitize, converted into a RDF format and uploaded into the database.

The implementation is still pretty much work in progress. It misses parts of the spec (there open questions about it) and might have some nasty bugs. You've been warned!

## Install

### Local

The project requires the following:

- Python >= 3.7
- [Poetry](https://python-poetry.org)

Once you have `poetry` installed, you can install the project locally by running the following commands in the repository dir (where the `pyproject.toml` file is located):

```sh
poetry install
poetry shell
```

### Using Docker

The application can be used with Docker. You first need to build the Docker Image by running:

```sh
docker build -t open-next/losh-krawler .
```

Then you can execute:

```sh
# display help
docker run --rm -u $UID open-next/losh-krawler --help

# mount config and run some command
docker run --rm -u $UID \
  -v "$PWD/config.yml:/opt/krawler/config.yml" \
  -v "$PWD/workdir:/opt/krawler/workdir" \
   krawler fetch url -c config.yml -vv "https://github.com/OPEN-NEXT/OKH-LOSH/blob/master/sample_data/okh-OHLOOM.toml"
```

## Usage

The application has a convenient CLI, that also explains itself, when you pass the `--help` flag to it. Here is a quick overview of the current available commands:

| Command | Description |
|--|---|
| `krawl convert <from> <to>` | Convert a manifest file from one format into another one. Supported formats: YAML (`.yml`, `.yaml`), TOML (`.toml`), RDF (`.ttl`) |
| `krawl fetch url <url1> [<urlN>...]` | Download and process metadata of selected projects. |
| `krawl fetch <platform>` | Search for projects on a given platform and download and process their metadata. |
| `krawl list fetchers` | List available fetchers, that can be used in `krawl fetch` command. |
| `krawl validate config <file>` | Validate a given configuration file. |
| `krawl validate manifest <file>` | Validate a given manifest file. |

Examples:

```sh
# fetch selected projects
krawl fetch url -c config.yml -v "https://github.com/OPEN-NEXT/OKH-LOSH/blob/master/sample_data/okh-sample-OHLOOM.toml"
krawl fetch url -c config.yml -v "https://wikifactory.com/+OttoDIY/otto-diy-plus"

# search and fetch all projects of a platform
krawl fetch github.com -c config.yml -v --report report.txt

# convert a local manifest file
krawl convert -v project.yml project.ttl

# validate a local manifest file
krawl validate -v project.yml
```

## Configuration

A sample configuration file with explanations can be found [here](sample-config.yml).

</s>
