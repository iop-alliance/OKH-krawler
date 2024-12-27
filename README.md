<!--
SPDX-FileCopyrightText: 2021 - 2022 Andre Lehmann <aisberg@posteo.de>
SPDX-FileCopyrightText: 2021 Alec Hanefeld <alec@hanefeld.eu>
SPDX-FileCopyrightText: 2021 Alec Hanefeld <alec@konek.to>
SPDX-FileCopyrightText: 2021 hoijui <hoijui.quaero@gmail.com>
SPDX-FileCopyrightText: 2021 moedn <45949491+moedn@users.noreply.github.com>
SPDX-FileCopyrightText: 2023 - 2024 Robin Vobruba <hoijui.quaero@gmail.com>

SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Open Know-How Krawler

A [crawler] for hardware design projects.

(In reality, it is more a [scraper])

---

_Back in **alpha** state!_
Please do not yet use for anything then experiments!

---

It leverages the _distributed ready_ [Open Know-How (OKH)][OKH]
[Library of Open Source Hardware (LOSH)](https://losh.opennext.eu).
The crawler currently searches:

- [GitHub](https://github.com),
- [OSHWA](https://certification.oshwa.org), and
- [Thingiverse](https://www.thingiverse.com)

for hardware design projects.

The projects raw data -
which is either the contents of an [OKH] meta-data (aka manifest) file,
or whatever the hosting platforms API
(or alternatively web interface) provides about the project -
is then stored as a file.
Next to it is an other file ([JSON]),
containing the crawling meta-data,
like the source URL and crawling date.

In a second step, all these files are then
parsed,
analyzed,
sanitized,
converted to a manifest file for the latest [OKH specification]
(except it is already in [RDF] format)
and then converted to [OKH] [RDF] data,
which is then stored in a file.

These files may then be hosted as-is in a git repo,
or fed into an [RDF] [Triple-Store] like [Apache Jena], [OxiGraph] or [neo4j]
Once such a project is found, its metadata is downloaded, parsed and sanitize,
converted into a [RDF] format and uploaded into the database.

## Install

### Local

The project requires the following:

- Python >= 3.10
- [Poetry](https://python-poetry.org)

Once you have `poetry` installed,
you can install the project locally
by running the following commands in the repository dir
(where the `pyproject.toml` file is located):

```sh
poetry install
poetry shell
```

Within that shell,
you should then have `krawl` in your _PATH_.
You can verify that with `krawl --help`.

### Using Docker

The application can be used with [Docker],
which you may need to install first.
You first need to acquire the docker image,
in either of these ways:

#### Install the Image

1. Build

    To build the Docker image yourself,
    in the local dir of the sources of this project,
    run:

    ```sh
    docker build --tag iopa/okh-krawler:latest .
    ```

2. Download

    Download the latest build of the docker image with:

    ```sh
    docker pull iopa/okh-krawler:latest
    ```

#### Run

Then you can execute:

```sh
# display help
docker run --rm --user $UID iopa/okh-krawler:latest --help

# mount config and run some command
docker run --rm --user $UID \
  --volume "$PWD/config.yml:/opt/krawler/config.yml" \
  --volume "$PWD/workdir:/opt/krawler/workdir" \
  iopa/okh-krawler:latest \
  fetch url \
    --config config.yml \
    -vv \
    "https://github.com/iop-alliance/OpenKnowHow/blob/master/res/sample_data/okh-OHLOOM.toml"
```

## Usage

The application has a convenient [CLI],
that also explains itself when you pass the `--help` flag to it.
Here is a quick overview of the current available commands
(make sure you are within the poetry shell when executing these):

| Command | Description |
|--|---|
| `krawl convert <from> <to>` | Convert a manifest file from one format into another one. Supported formats: [YAML] (`.yml`, `.yaml`), [TOML] (`.toml`), [RDF] (`.ttl`) |
| `krawl fetch url <url1> [<urlN>...]` | Download and process metadata of selected projects. |
| `krawl fetch <platform>` | Search for projects on a given platform and download and process their metadata. |
| `krawl list fetchers` | List available fetchers, that can be used in `krawl fetch` command. |
| `krawl validate config <file>` | Validate a given configuration file. |
| `krawl validate manifest <file>` | Validate a given manifest file. |

Examples:

```sh
# fetch selected projects
krawl fetch url -c config.yml -vv "https://github.com/iop-alliance/OpenKnowHow/blob/master/res/sample_data/okh-sample-OHLOOM.toml"
krawl fetch url -c config.yml -vv "https://www.thingiverse.com/thing:3062487"

# search and fetch all projects of a platform
krawl fetch github.com -c config.yml -vv --report report.txt

# convert a local manifest file
krawl convert -vv project.yml project.ttl

# validate a local manifest file
krawl validate -vv project.yml
```

## Configuration

A sample configuration file with explanations
can be found in [sample-config.yml](sample-config.yml).

## Development

### Release a new version

Make sure you have the latest version
of the `bump-my-version` tool installed:

```shell
pip install --upgrade bump-my-version
```

Then, to see what would happen without actually doing anything,
try these commands:

```shell
bump-my-version bump patch --dry-run -v --allow-dirty
bump-my-version bump minor --dry-run -v --allow-dirty
bump-my-version bump major --dry-run -v --allow-dirty
bump-my-version bump --dry-run -v --allow-dirty --new-version 3.0.0
bump-my-version bump --help
```

To actually execute a release,
which crates a git tag, and commits changes to files,
choose one of these commands:

```shell
bump-my-version bump patch -v
bump-my-version bump minor -v
bump-my-version bump major -v
bump-my-version bump -v --new-version 3.0.0
```

And then push the changes; done!

[Apache Jena]: https://jena.apache.org/
[crawler]: https://en.wikipedia.org/wiki/Web_crawler
[neo4j]: http://neo4j.org/
[OKH]: https://github.com/iop-alliance/OpenKnowHow
[OKH specification]: https://github.com/iop-alliance/OpenKnowHow
[OxiGraph]: https://github.com/oxigraph/oxigraph
[RDF]: https://en.wikipedia.org/wiki/Resource_Description_Framework
[scraper]: https://en.wikipedia.org/wiki/Data_scraping
[Triple-Store]: https://en.wikipedia.org/wiki/Triplestore
[CLI]: https://en.wikipedia.org/wiki/Command-line_interface
[TOML]: https://en.wikipedia.org/wiki/TOML
[YAML]: https://en.wikipedia.org/wiki/YAML
[JSON]: https://en.wikipedia.org/wiki/JSON
[Docker]: https://en.wikipedia.org/wiki/Docker_(software)
