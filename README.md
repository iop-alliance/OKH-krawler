# oshi-crawl

oshi crawler

## Setup

### Requirements
Python >= 3.6

[poetry](https://python-poetry.org)

See [here](https://python-poetry.org/docs/) how to install poetry

Once you have `poetry` in your PATH, install the project by entering the `krawl` dir (where the `pyproject.toml` file is located) and typing

`poetry install`

`poetry shell`

All commands in the `bin/` directory expect the `poetry shell` to be active.

### Credentials
All environment variables in the `.env.example` file must be defined.

You might want to use [direnv](https://direnv.net/) to automatically source the `.env` file you created.

Wikibase specifc env variables:

`KRAWLER_WB_USER="..."`

`KRAWLER_WB_PASSWORD="..."`

Wikibase OAuth client:

`KRAWLER_WB_CONSUMER_KEY="..."`

`KRAWLER_WB_CONSUMER_SECRET="..."`

`KRAWLER_WB_ACCESS_TOKEN="..."`

`KRAWLER_WB_ACCESS_SECRET="..."`

(ask your wikibase admin if you are unsure how to get this)

Github specific env variables:
`KRAWLER_GITHUB_KEY="..."`
(get one [here](https://github.com/settings/tokens)

This can be any directory where the krawler can write its intermediary files.
`KRAWLER_WORKDIR="..."`

## Execute

`krawl/bin/gh.sh`

To fetch project from github

`krawl/bin/wf.sh`

To fetch projects from wikifactory

`krawl/bin/wikibase.sh`

To push all found projects to wikibase

(note that the pusher currently always pushes every file it finds, even if it has already been pushed)

If you want to push an individual `ttl` file you can also use:

`python -m krawl.wikibase.core ./samples/okh-sample-OHLOOM_fixed.ttl`
