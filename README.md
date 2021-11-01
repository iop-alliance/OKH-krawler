# LOSH-Krawler

## Setup

### Requirements

* Python >= 3.6
* [poetry](https://python-poetry.org)
  (see [here](https://python-poetry.org/docs/) how to install it)

Once you have `poetry` in your PATH, install the project by entering the `krawl` dir (where the `pyproject.toml` file is located) and type:

```sh
poetry install
poetry shell
```

All commands in the `bin/` directory expect the `poetry shell` to be active.

### Credentials

All environment variables in the `.env.example` file must be defined.
You might want to use [direnv](https://direnv.net/) to automatically source the `.env` file you created.

```bash
# This can be any directory where the krawler can write its intermediary files,
# (just make sure it is not in a git dir or ignored by git,
# as it will contain a lot of files):
KRAWLER_WORKDIR="..."

# Wikibase specifc env variables
KRAWLER_WB_USER="..."
KRAWLER_WB_PASSWORD="..."

# Wikibase OAuth client
KRAWLER_WB_CONSUMER_KEY="..."
KRAWLER_WB_CONSUMER_SECRET="..."
KRAWLER_WB_ACCESS_TOKEN="..."
KRAWLER_WB_ACCESS_SECRET="..."
# (... ask your wikibase admin if you are unsure how to get this)

# Wikibase Reconciler Prop ID
# This is the id (ie. P123) of a wikibase property of type URL and ideally name "id".
# This property has to be created in wikibase and then set here.
KRAWLER_WB_RECONCILEPROPID="..."

# GitHub specific env variables
KRAWLER_GITHUB_KEY="..."
# (... get one [here](https://github.com/settings/tokens)
```

## Execute

To fetch project from GitHub
```sh
krawl/bin/fetch/github/gh.sh
```

To fetch projects from wikifactory
```sh
krawl/bin/fetch/wikifactory/wf.sh
```

To convert all TOML to RDF (turtle, ttl)
```sh
krawl/bin/push/wikibase.sh
krawl/bin/push/rdf.sh
```

To push all found projects to wikibase
(note that the pusher currently always pushes every file it finds, even if it has already been pushed)

If you want to push an individual `ttl` file you can also use:
```sh
python -m krawl.wikibase.core ./samples/okh-sample-OHLOOM_fixed.ttl
```
